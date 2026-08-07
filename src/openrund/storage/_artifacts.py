"""Immutable integrity-checked Artifact metadata and local blob custody."""

from __future__ import annotations

import asyncio
import errno
import hashlib
import os
import secrets
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Final, Self, final

from openrund._localfs import (
    LocalFilesystemError,
    fsync_directory,
    regular_file_status,
    secure_directory_tree,
)
from openrund.codec import decode_json_value, encode_json_value
from openrund.contracts.ids import ArtifactId
from openrund.contracts.json import MISSING, JsonObject, MissingType
from openrund.contracts.time import Timestamp
from openrund.errors import (
    OpenRundError,
    ResourceClosedError,
    StorageError,
    StorageIntegrityError,
    ValidationError,
)
from openrund.paths import PathInput, normalize_local_path
from openrund.ports.artifacts import ArtifactBlob, ArtifactEntry
from openrund.storage._database import _Database


def _artifact_component(artifact_id: object) -> str:
    if not isinstance(artifact_id, ArtifactId):
        raise ValidationError(code="artifact_id_type_invalid")
    value = artifact_id.value
    if (
        value == ""
        or value in {".", ".."}
        or "\x00" in value
        or "/" in value
        or "\\" in value
        or PureWindowsPath(value).drive != ""
        or (os.altsep is not None and os.altsep in value)
    ):
        raise ValidationError(code="artifact_id_component_invalid")
    return value


def _ensure_directory(path: Path) -> None:
    try:
        secure_directory_tree(path, create=True)
    except LocalFilesystemError as error:
        if error.reason == "symlink":
            raise StorageError(code="artifact_root_symlink") from None
        if error.reason == "not_directory":
            raise StorageError(code="artifact_root_not_directory") from None
        if error.reason == "create":
            raise StorageError(code="artifact_root_create_failed") from None
        raise StorageError(code="artifact_root_inspection_failed") from None


def _materialize_directory(path: Path) -> None:
    _ensure_directory(path)


def _regular_file(path: Path, *, code: str) -> os.stat_result:
    try:
        return regular_file_status(path)
    except LocalFilesystemError as error:
        if error.reason == "inspect":
            raise StorageError(code="artifact_blob_inspection_failed") from None
        raise StorageIntegrityError(code=code) from None


def _fsync_directory(path: Path) -> None:
    try:
        fsync_directory(path)
    except LocalFilesystemError:
        raise StorageError(code="artifact_sync_failed") from None


def _missing_if_none[T](value: T | MissingType | None) -> T | MissingType:
    return MISSING if value is None else value


def _normalized_entry(artifact: ArtifactEntry) -> ArtifactEntry:
    return ArtifactEntry(
        artifact_id=artifact.artifact_id,
        kind=artifact.kind,
        created_at=artifact.created_at,
        content_type=_missing_if_none(artifact.content_type),
        byte_length=_missing_if_none(artifact.byte_length),
        sha256=_missing_if_none(artifact.sha256),
        metadata=_missing_if_none(artifact.metadata),
        unavailable_at=_missing_if_none(artifact.unavailable_at),
    )


def _metadata_json(artifact: ArtifactEntry) -> str:
    value = None if isinstance(artifact.metadata, MissingType) else artifact.metadata
    return encode_json_value(value).decode("utf-8")[:-1]


def _required_text(row: sqlite3.Row, name: str) -> str:
    value = row[name]
    if not isinstance(value, str):
        raise StorageIntegrityError(code="artifact_row_invalid")
    return value


def _optional_text(row: sqlite3.Row, name: str) -> str | None:
    value = row[name]
    if value is not None and not isinstance(value, str):
        raise StorageIntegrityError(code="artifact_row_invalid")
    return value


def _missing_text(row: sqlite3.Row, name: str) -> str | MissingType:
    value = _optional_text(row, name)
    return MISSING if value is None else value


@dataclass(frozen=True, slots=True)
class _StoredArtifact:
    entry: ArtifactEntry
    blob_path: str | None


def _decode_stored(row: sqlite3.Row) -> _StoredArtifact:
    try:
        metadata_value = decode_json_value(_required_text(row, "metadata_json") + "\n")
        if metadata_value is not None and not isinstance(metadata_value, JsonObject):
            raise StorageIntegrityError(code="artifact_row_invalid")
        byte_length = row["byte_length"]
        if byte_length is not None and (
            isinstance(byte_length, bool) or not isinstance(byte_length, int)
        ):
            raise StorageIntegrityError(code="artifact_row_invalid")
        unavailable = _optional_text(row, "unavailable_at")
        entry = ArtifactEntry(
            artifact_id=ArtifactId(value=_required_text(row, "artifact_id")),
            kind=_required_text(row, "kind"),
            created_at=Timestamp(value=_required_text(row, "created_at")),
            content_type=_missing_text(row, "content_type"),
            byte_length=MISSING if byte_length is None else byte_length,
            sha256=_missing_text(row, "sha256"),
            metadata=MISSING if metadata_value is None else metadata_value,
            unavailable_at=MISSING if unavailable is None else Timestamp(value=unavailable),
        )
        _artifact_component(entry.artifact_id)
        return _StoredArtifact(entry=entry, blob_path=_optional_text(row, "blob_path"))
    except StorageIntegrityError:
        raise
    except (OpenRundError, KeyError, TypeError, ValueError, UnicodeError):
        raise StorageIntegrityError(code="artifact_row_invalid") from None


_ARTIFACT_COLUMNS: Final = (
    "artifact_id, kind, created_at, content_type, byte_length, metadata_json, "
    "blob_path, unavailable_at, sha256"
)
_ARTIFACT_SELECT: Final = f"SELECT {_ARTIFACT_COLUMNS} FROM artifacts WHERE artifact_id = ?"
_ARTIFACT_FAULT_POINTS: Final = frozenset(
    {"after_staging", "after_publish", "before_metadata_commit", "after_metadata_commit"}
)


class _ArtifactCrash(BaseException):
    """Private process-stop simulation that deliberately bypasses cleanup."""


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactRecoverySummary:
    """Safe immutable result of one explicit Artifact recovery pass."""

    removed_stages: int
    quarantined_orphans: tuple[ArtifactId, ...]
    unavailable_artifacts: tuple[ArtifactId, ...]
    verified_artifacts: tuple[ArtifactId, ...]

    def __post_init__(self) -> None:
        if (
            isinstance(self.removed_stages, bool)
            or not isinstance(self.removed_stages, int)
            or self.removed_stages < 0
        ):
            raise ValidationError(code="artifact_recovery_count_invalid")
        for value in (
            self.quarantined_orphans,
            self.unavailable_artifacts,
            self.verified_artifacts,
        ):
            if any(not isinstance(item, ArtifactId) for item in value):
                raise ValidationError(code="artifact_recovery_ids_invalid")


@final
class SqliteArtifactStore:
    """SQLite metadata plus absent-only local blob publication."""

    def __init__(
        self,
        database_path: PathInput,
        artifact_root: PathInput,
        *,
        busy_timeout_ms: int = 5_000,
        _fail_at: str | None = None,
    ) -> None:
        if _fail_at is not None and _fail_at not in _ARTIFACT_FAULT_POINTS:
            raise ValidationError(code="artifact_fault_point_invalid")
        self._database = _Database(database_path, busy_timeout_ms=busy_timeout_ms)
        self._root = Path(normalize_local_path(artifact_root).path)
        self._staging = self._root / "staging"
        self._blobs = self._root / "blobs"
        self._orphans = self._root / "orphans"
        self._fail_at = _fail_at
        self._closed = False
        self._prepare_directories()

    async def __aenter__(self) -> Self:
        if self._closed:
            raise ResourceClosedError(resource="artifact_store")
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: object | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise ResourceClosedError(resource="artifact_store")

    @property
    def root(self) -> Path:
        return self._root

    async def put(self, artifact: ArtifactEntry, /, *, blob: ArtifactBlob | None = None) -> None:
        self._ensure_open()
        if not isinstance(artifact, ArtifactEntry):
            raise ValidationError(code="artifact_put_entry_invalid")
        if blob is not None and not isinstance(blob, ArtifactBlob):
            raise ValidationError(code="artifact_put_blob_invalid")
        normalized = _normalized_entry(artifact)
        component = _artifact_component(normalized.artifact_id)
        copied_blob = None if blob is None else self._validate_blob(normalized, blob)
        await asyncio.to_thread(self._put_sync, normalized, component, copied_blob)

    async def get(self, artifact_id: ArtifactId, /) -> ArtifactEntry | None:
        self._ensure_open()
        component = _artifact_component(artifact_id)
        return await self._database.read(
            lambda connection: (
                None
                if (row := connection.execute(_ARTIFACT_SELECT, (component,)).fetchone()) is None
                else _decode_stored(row).entry
            )
        )

    async def get_blob(self, artifact_id: ArtifactId, /) -> ArtifactBlob | None:
        self._ensure_open()
        component = _artifact_component(artifact_id)
        return await asyncio.to_thread(self._get_blob_sync, component)

    async def mark_unavailable(self, artifact_id: ArtifactId, unavailable_at: Timestamp, /) -> None:
        self._ensure_open()
        component = _artifact_component(artifact_id)
        if not isinstance(unavailable_at, Timestamp):
            raise ValidationError(code="artifact_unavailable_timestamp_invalid")

        def update(connection: sqlite3.Connection) -> None:
            row = connection.execute(_ARTIFACT_SELECT, (component,)).fetchone()
            if row is None:
                raise StorageIntegrityError(code="artifact_not_found")
            stored = _decode_stored(row)
            current = stored.entry.unavailable_at
            if not isinstance(current, MissingType):
                if current == unavailable_at:
                    return
                raise StorageIntegrityError(code="artifact_immutable")
            connection.execute(
                "UPDATE artifacts SET unavailable_at = ? WHERE artifact_id = ?",
                (unavailable_at.value, component),
            )

        await self._database.write(update)

    async def recover(self, unavailable_at: Timestamp, /) -> ArtifactRecoverySummary:
        self._ensure_open()
        """Repair known split-custody states using an explicit observation time."""

        if not isinstance(unavailable_at, Timestamp):
            raise ValidationError(code="artifact_recovery_timestamp_invalid")
        return await asyncio.to_thread(self._recover_sync, unavailable_at)

    def _prepare_directories(self) -> None:
        for directory in (self._root, self._staging, self._blobs, self._orphans):
            _materialize_directory(directory)
        try:
            resolved_root = self._root.resolve(strict=True)
            for directory in (self._staging, self._blobs, self._orphans):
                if not directory.resolve(strict=True).is_relative_to(resolved_root):
                    raise StorageError(code="artifact_root_containment_failed")
        except StorageError:
            raise
        except OSError as error:
            raise StorageError(code="artifact_root_containment_failed") from error

    @staticmethod
    def _validate_blob(artifact: ArtifactEntry, blob: ArtifactBlob) -> bytes:
        content = memoryview(blob.content).tobytes()
        digest = hashlib.sha256(content).hexdigest()
        if artifact.byte_length != len(content) or artifact.sha256 != digest:
            raise StorageIntegrityError(code="artifact_integrity_mismatch")
        blob_content_type = _missing_if_none(blob.content_type)
        if not isinstance(blob_content_type, MissingType) and (
            artifact.content_type != blob_content_type
        ):
            raise StorageIntegrityError(code="artifact_content_type_mismatch")
        if not isinstance(artifact.unavailable_at, MissingType):
            raise StorageIntegrityError(code="artifact_blob_unavailable")
        return content

    def _select_sync(self, component: str) -> _StoredArtifact | None:
        def select(connection: sqlite3.Connection) -> _StoredArtifact | None:
            row = connection.execute(_ARTIFACT_SELECT, (component,)).fetchone()
            return None if row is None else _decode_stored(row)

        return self._database.read_sync(select)

    def _relative_blob_path(self, component: str) -> str:
        return f"blobs/{component}.blob"

    def _blob_path(self, component: str, relative: str) -> Path:
        portable = PurePosixPath(relative)
        if (
            portable.is_absolute()
            or portable.parts != ("blobs", f"{component}.blob")
            or "\\" in relative
        ):
            raise StorageIntegrityError(code="artifact_blob_path_invalid")
        path = self._root.joinpath(*portable.parts)
        try:
            if not path.parent.resolve(strict=True).is_relative_to(self._root.resolve(strict=True)):
                raise StorageIntegrityError(code="artifact_blob_path_invalid")
        except StorageIntegrityError:
            raise
        except OSError as error:
            raise StorageError(code="artifact_blob_inspection_failed") from error
        return path

    def _read_verified_blob(self, path: Path, *, byte_length: int, sha256: str) -> bytes:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except FileNotFoundError:
            raise StorageIntegrityError(code="artifact_blob_missing") from None
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise StorageIntegrityError(code="artifact_blob_missing") from None
            raise StorageError(code="artifact_blob_read_failed") from error
        try:
            status = os.fstat(descriptor)
            if not stat.S_ISREG(status.st_mode):
                raise StorageIntegrityError(code="artifact_blob_missing")
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                content = stream.read()
        except StorageIntegrityError:
            raise
        except OSError as error:
            raise StorageError(code="artifact_blob_read_failed") from error
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        if status.st_size != byte_length:
            raise StorageIntegrityError(code="artifact_blob_corrupt")
        if len(content) != byte_length or hashlib.sha256(content).hexdigest() != sha256:
            raise StorageIntegrityError(code="artifact_blob_corrupt")
        return content

    def _get_blob_sync(self, component: str) -> ArtifactBlob | None:
        stored = self._select_sync(component)
        if stored is None or stored.blob_path is None:
            return None
        if not isinstance(stored.entry.unavailable_at, MissingType):
            return None
        if not isinstance(stored.entry.byte_length, int) or not isinstance(
            stored.entry.sha256, str
        ):
            raise StorageIntegrityError(code="artifact_blob_metadata_invalid")
        path = self._blob_path(component, stored.blob_path)
        content = self._read_verified_blob(
            path,
            byte_length=stored.entry.byte_length,
            sha256=stored.entry.sha256,
        )
        return ArtifactBlob(
            content=memoryview(content).tobytes(),
            content_type=stored.entry.content_type,
        )

    def _assert_existing(
        self,
        existing: _StoredArtifact,
        artifact: ArtifactEntry,
        component: str,
        blob: bytes | None,
    ) -> None:
        if existing.entry != artifact:
            raise StorageIntegrityError(code="artifact_immutable")
        if blob is None:
            if existing.blob_path is None:
                return
            raise StorageIntegrityError(code="artifact_immutable")
        if existing.blob_path is None:
            raise StorageIntegrityError(code="artifact_immutable")
        if not isinstance(artifact.byte_length, int) or not isinstance(artifact.sha256, str):
            raise StorageIntegrityError(code="artifact_blob_metadata_invalid")
        current = self._read_verified_blob(
            self._blob_path(component, existing.blob_path),
            byte_length=artifact.byte_length,
            sha256=artifact.sha256,
        )
        if current != blob:
            raise StorageIntegrityError(code="artifact_immutable")

    def _write_stage(self, path: Path, content: bytes) -> None:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            _fsync_directory(self._staging)
        except FileExistsError:
            raise StorageIntegrityError(code="artifact_stage_collision") from None
        except OSError as error:
            raise StorageError(code="artifact_blob_write_failed") from error

    def _checkpoint(self, name: str) -> None:
        if self._fail_at == name:
            raise _ArtifactCrash(name)

    def _commit_metadata(
        self,
        artifact: ArtifactEntry,
        component: str,
        relative_blob: str | None,
        blob: bytes | None,
    ) -> None:
        def commit(connection: sqlite3.Connection) -> None:
            row = connection.execute(_ARTIFACT_SELECT, (component,)).fetchone()
            if row is not None:
                self._assert_existing(_decode_stored(row), artifact, component, blob)
                return
            connection.execute(
                "INSERT INTO artifacts "
                "(artifact_id, kind, created_at, content_type, byte_length, metadata_json, "
                "blob_path, unavailable_at, sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    component,
                    artifact.kind,
                    artifact.created_at.value,
                    None
                    if isinstance(artifact.content_type, MissingType)
                    else artifact.content_type,
                    None if isinstance(artifact.byte_length, MissingType) else artifact.byte_length,
                    _metadata_json(artifact),
                    relative_blob,
                    artifact.unavailable_at.value
                    if isinstance(artifact.unavailable_at, Timestamp)
                    else None,
                    None if isinstance(artifact.sha256, MissingType) else artifact.sha256,
                ),
            )

        self._database.write_sync(commit)

    def _put_sync(self, artifact: ArtifactEntry, component: str, blob: bytes | None) -> None:
        self._prepare_directories()
        existing = self._select_sync(component)
        if existing is not None:
            self._assert_existing(existing, artifact, component, blob)
            return
        if blob is None:
            self._commit_metadata(artifact, component, None, None)
            return

        relative_blob = self._relative_blob_path(component)
        final_path = self._blob_path(component, relative_blob)
        stage_path = self._staging / f"{component}.{secrets.token_hex(16)}.stage"
        self._write_stage(stage_path, blob)
        preserve_stage = False
        try:
            self._checkpoint("after_staging")
            try:
                os.link(stage_path, final_path, follow_symlinks=False)
            except FileExistsError:
                if not isinstance(artifact.byte_length, int) or not isinstance(
                    artifact.sha256, str
                ):
                    raise StorageIntegrityError(code="artifact_blob_metadata_invalid") from None
                current = self._read_verified_blob(
                    final_path,
                    byte_length=artifact.byte_length,
                    sha256=artifact.sha256,
                )
                if current != blob:
                    raise StorageIntegrityError(code="artifact_immutable") from None
            except OSError as error:
                raise StorageError(code="artifact_blob_publish_failed") from error
            self._checkpoint("after_publish")
            _fsync_directory(self._blobs)
            self._checkpoint("before_metadata_commit")
            self._commit_metadata(artifact, component, relative_blob, blob)
            self._checkpoint("after_metadata_commit")
        except BaseException as error:
            preserve_stage = not isinstance(error, Exception)
            raise
        finally:
            if not preserve_stage:
                try:
                    stage_path.unlink(missing_ok=True)
                    _fsync_directory(self._staging)
                except OSError as error:
                    raise StorageError(code="artifact_stage_cleanup_failed") from error

    @staticmethod
    def _stage_component(name: str) -> str | None:
        if not name.endswith(".stage"):
            return None
        stem = name[: -len(".stage")]
        component, separator, token = stem.rpartition(".")
        if (
            separator == ""
            or len(token) != 32
            or any(character not in "0123456789abcdef" for character in token)
        ):
            return None
        try:
            return _artifact_component(ArtifactId(value=component))
        except OpenRundError:
            return None

    @staticmethod
    def _blob_component(name: str) -> str | None:
        if not name.endswith(".blob"):
            return None
        component = name[: -len(".blob")]
        try:
            return _artifact_component(ArtifactId(value=component))
        except OpenRundError:
            return None

    @staticmethod
    def _regular_entries(directory: Path) -> tuple[os.DirEntry[str], ...]:
        try:
            with os.scandir(directory) as entries:
                return tuple(
                    entry
                    for entry in entries
                    if not entry.is_symlink() and entry.is_file(follow_symlinks=False)
                )
        except OSError as error:
            raise StorageError(code="artifact_recovery_scan_failed") from error

    def _remove_stages(self) -> int:
        removed = 0
        for entry in self._regular_entries(self._staging):
            if self._stage_component(entry.name) is None:
                continue
            try:
                Path(entry.path).unlink()
            except OSError as error:
                raise StorageError(code="artifact_recovery_remove_failed") from error
            removed += 1
        if removed:
            _fsync_directory(self._staging)
        return removed

    def _all_stored_sync(self) -> dict[str, _StoredArtifact]:
        def select(connection: sqlite3.Connection) -> dict[str, _StoredArtifact]:
            rows = connection.execute(
                f"SELECT {_ARTIFACT_COLUMNS} FROM artifacts ORDER BY artifact_id"
            ).fetchall()
            stored = tuple(_decode_stored(row) for row in rows)
            return {item.entry.artifact_id.value: item for item in stored}

        return self._database.read_sync(select)

    def _quarantine_orphan(self, source: Path, component: str) -> None:
        target = self._orphans / f"{component}.blob"
        try:
            os.link(source, target, follow_symlinks=False)
        except FileExistsError:
            source_status = _regular_file(source, code="artifact_orphan_invalid")
            target_status = _regular_file(target, code="artifact_orphan_collision")
            if not os.path.samestat(source_status, target_status):
                raise StorageIntegrityError(code="artifact_orphan_collision") from None
        except OSError as error:
            raise StorageError(code="artifact_orphan_quarantine_failed") from error
        try:
            source.unlink()
            _fsync_directory(self._blobs)
            _fsync_directory(self._orphans)
        except OSError as error:
            raise StorageError(code="artifact_orphan_quarantine_failed") from error

    def _mark_recovery_unavailable(
        self, components: tuple[str, ...], unavailable_at: Timestamp
    ) -> None:
        if not components:
            return

        def update(connection: sqlite3.Connection) -> None:
            connection.executemany(
                "UPDATE artifacts SET unavailable_at = ? "
                "WHERE artifact_id = ? AND unavailable_at IS NULL",
                ((unavailable_at.value, component) for component in components),
            )

        self._database.write_sync(update)

    def _recover_sync(self, unavailable_at: Timestamp) -> ArtifactRecoverySummary:
        self._prepare_directories()
        removed_stages = self._remove_stages()
        stored = self._all_stored_sync()
        quarantined: list[str] = []

        for entry in self._regular_entries(self._blobs):
            component = self._blob_component(entry.name)
            if component is None:
                continue
            record = stored.get(component)
            expected_relative = self._relative_blob_path(component)
            if record is None or record.blob_path != expected_relative:
                self._quarantine_orphan(Path(entry.path), component)
                quarantined.append(component)

        unavailable: list[str] = []
        verified: list[str] = []
        for component, record in stored.items():
            if record.blob_path is None or not isinstance(record.entry.unavailable_at, MissingType):
                continue
            try:
                if not isinstance(record.entry.byte_length, int) or not isinstance(
                    record.entry.sha256, str
                ):
                    raise StorageIntegrityError(code="artifact_blob_metadata_invalid")
                self._read_verified_blob(
                    self._blob_path(component, record.blob_path),
                    byte_length=record.entry.byte_length,
                    sha256=record.entry.sha256,
                )
            except StorageIntegrityError:
                unavailable.append(component)
            else:
                verified.append(component)

        unavailable_tuple = tuple(sorted(set(unavailable)))
        self._mark_recovery_unavailable(unavailable_tuple, unavailable_at)
        return ArtifactRecoverySummary(
            removed_stages=removed_stages,
            quarantined_orphans=tuple(
                ArtifactId(value=component) for component in sorted(set(quarantined))
            ),
            unavailable_artifacts=tuple(
                ArtifactId(value=component) for component in unavailable_tuple
            ),
            verified_artifacts=tuple(
                ArtifactId(value=component) for component in sorted(set(verified))
            ),
        )
