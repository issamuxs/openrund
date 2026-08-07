"""Immutable result contracts for deterministic View replay."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, final

from openrund.contracts.ids import RunId

if TYPE_CHECKING:
    from openrund.contracts.ids import ActionId, ArtifactId
    from openrund.views._actions import (
        ActionReceipt,
        ActionReconciliationView,
        ActionStatusEntry,
    )
    from openrund.views._artifacts import ArtifactIndexEntry
    from openrund.views._checkpoints import CheckpointView
    from openrund.views._delegation import DelegationView
    from openrund.views._reports import CheckReport
    from openrund.views._run_status import RunStatusView
    from openrund.views._timeline import TimelineEntry
    from openrund.views._waits import WaitQueues


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class RunViewBundle:
    """Every derived surface for one complete history and watermark."""

    run_status: RunStatusView
    timeline: tuple[TimelineEntry, ...]
    action_status: Mapping[ActionId, ActionStatusEntry]
    action_reconciliation: ActionReconciliationView
    action_receipts: Mapping[ActionId, ActionReceipt]
    artifact_index: Mapping[ArtifactId, ArtifactIndexEntry]
    checkpoints: CheckpointView
    delegation: DelegationView
    waits: WaitQueues
    reports: tuple[CheckReport, ...]


class ReplayIssueCode(StrEnum):
    WATERMARK_UNKNOWN = "watermark_unknown"
    WATERMARK_INVALID = "watermark_invalid"
    HISTORY_INPUT_INVALID = "history_input_invalid"
    HISTORY_EVENT_INVALID = "history_event_invalid"
    HISTORY_MIXED_RUN = "history_mixed_run"
    HISTORY_POSITION_DUPLICATE = "history_position_duplicate"
    HISTORY_OUT_OF_ORDER = "history_out_of_order"
    HISTORY_BEYOND_WATERMARK = "history_beyond_watermark"
    HISTORY_INCOMPLETE = "history_incomplete"
    ARTIFACT_INPUT_INVALID = "artifact_input_invalid"
    ARTIFACT_CONFLICT = "artifact_conflict"
    ARTIFACT_MIXED_RUN = "artifact_mixed_run"


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class ReplayIssue:
    """One safe reason why a replay boundary is not authoritative."""

    code: ReplayIssueCode
    position: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, ReplayIssueCode):
            raise TypeError("replay_issue_code_invalid")
        if self.position is not None and (
            not isinstance(self.position, int)
            or isinstance(self.position, bool)
            or self.position < 0
        ):
            raise ValueError("replay_issue_position_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteViewReplay[TViewBundle]:
    """A View result proven complete at its declared Event watermark."""

    watermark: int
    run_id: RunId | None
    views: TViewBundle

    def __post_init__(self) -> None:
        if (
            not isinstance(self.watermark, int)
            or isinstance(self.watermark, bool)
            or self.watermark < 0
        ):
            raise ValueError("replay_watermark_invalid")
        if self.run_id is not None and not isinstance(self.run_id, RunId):
            raise TypeError("replay_run_id_invalid")


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class IncompleteViewReplay:
    """A fail-closed replay result that deliberately contains no View bundle."""

    declared_watermark: int | None
    observed_positions: tuple[int, ...]
    issues: tuple[ReplayIssue, ...]

    def __post_init__(self) -> None:
        if self.declared_watermark is not None and (
            not isinstance(self.declared_watermark, int)
            or isinstance(self.declared_watermark, bool)
            or self.declared_watermark < 0
        ):
            raise ValueError("replay_watermark_invalid")
        if any(
            not isinstance(position, int) or isinstance(position, bool) or position < 1
            for position in self.observed_positions
        ):
            raise ValueError("replay_observed_positions_invalid")
        if not self.issues or any(not isinstance(issue, ReplayIssue) for issue in self.issues):
            raise ValueError("replay_issues_invalid")
