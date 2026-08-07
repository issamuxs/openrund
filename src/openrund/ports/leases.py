"""Domain-valued Lease coordination contracts without lock behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, final

from openrund.contracts.ids import LeaseId, RunId
from openrund.contracts.runs import Lease
from openrund.contracts.time import Timestamp
from openrund.errors import ValidationError

_MAX_SAFE_INTEGER = 9_007_199_254_740_991


def _common(run_id: object, owner: object, ttl_ms: object, now: object, code: str) -> None:
    if not isinstance(run_id, RunId):
        raise ValidationError(code=f"{code}_run_id_invalid")
    if not isinstance(owner, str) or owner == "":
        raise ValidationError(code=f"{code}_owner_invalid")
    if (
        isinstance(ttl_ms, bool)
        or not isinstance(ttl_ms, int)
        or not 1 <= ttl_ms <= _MAX_SAFE_INTEGER
    ):
        raise ValidationError(code=f"{code}_ttl_invalid")
    if not isinstance(now, Timestamp):
        raise ValidationError(code=f"{code}_timestamp_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LeaseAcquireInput:
    run_id: RunId
    owner: str
    ttl_ms: int
    now: Timestamp

    def __post_init__(self) -> None:
        _common(self.run_id, self.owner, self.ttl_ms, self.now, "lease_acquire")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class LeaseRenewInput:
    lease_id: LeaseId
    run_id: RunId
    owner: str
    token: str
    ttl_ms: int
    now: Timestamp

    def __post_init__(self) -> None:
        if not isinstance(self.lease_id, LeaseId):
            raise ValidationError(code="lease_renew_lease_id_invalid")
        _common(self.run_id, self.owner, self.ttl_ms, self.now, "lease_renew")
        if not isinstance(self.token, str) or self.token == "":
            raise ValidationError(code="lease_renew_token_invalid")


class LeaseStore(Protocol):
    async def acquire(self, value: LeaseAcquireInput, /) -> Lease | None: ...

    async def renew(self, value: LeaseRenewInput, /) -> Lease | None: ...

    async def release(self, lease_id: LeaseId, token: str, /) -> bool: ...

    async def get_active(self, run_id: RunId, now: Timestamp, /) -> Lease | None: ...
