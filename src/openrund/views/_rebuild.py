"""Aggregate known-watermark View reconstruction."""

from __future__ import annotations

from collections.abc import Iterable

from openrund.contracts.events import RuntimeEvent
from openrund.contracts.runs import Artifact
from openrund.views._actions import reduce_actions
from openrund.views._artifacts import reduce_artifact_index
from openrund.views._checkpoints import reduce_checkpoints
from openrund.views._delegation import reduce_delegation
from openrund.views._history import KnownHistory, prepare_history
from openrund.views._model import CompleteViewReplay, IncompleteViewReplay, RunViewBundle
from openrund.views._reports import reduce_reports
from openrund.views._run_status import reduce_run_status
from openrund.views._timeline import reduce_timeline
from openrund.views._waits import reduce_waits


def rebuild_views(
    events: Iterable[RuntimeEvent],
    *,
    watermark: int | None,
    artifacts: Iterable[Artifact] = (),
) -> CompleteViewReplay[RunViewBundle] | IncompleteViewReplay:
    """Validate exact history, then compose every immutable View surface once."""

    history = prepare_history(events, watermark=watermark, artifacts=artifacts)
    if not isinstance(history, KnownHistory):
        return history

    action_views = reduce_actions(history)
    artifact_index = reduce_artifact_index(history)
    waits = reduce_waits(history)
    bundle = RunViewBundle(
        run_status=reduce_run_status(
            history,
            waits=waits,
            actions=action_views,
            artifact_index=artifact_index,
        ),
        timeline=reduce_timeline(history),
        action_status=action_views.status,
        action_reconciliation=action_views.reconciliation,
        action_receipts=action_views.receipts,
        artifact_index=artifact_index,
        checkpoints=reduce_checkpoints(history),
        delegation=reduce_delegation(history),
        waits=waits,
        reports=reduce_reports(history),
    )
    return CompleteViewReplay(
        watermark=history.watermark,
        run_id=history.run_id,
        views=bundle,
    )
