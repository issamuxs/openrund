from __future__ import annotations

import asyncio
from pathlib import Path

from openrund.bundles import export_bundle, replay_bundle

from .conftest import BundleSource


def test_replay_returns_verified_history_without_store_writes(
    tmp_path: Path, bundle_source: BundleSource
) -> None:
    exported = asyncio.run(
        export_bundle(
            run_id=bundle_source.run_id,
            output_path=tmp_path / "run.orun",
            event_store=bundle_source.event_store,
            artifact_store=bundle_source.artifact_store,
            exported_at=bundle_source.timestamp,
        )
    )
    calls_before = bundle_source.event_store.calls
    replay = replay_bundle(exported.bundle_path)
    assert replay.events == bundle_source.events
    assert replay.views.run_status.status == "running"
    assert replay.views.run_status.source_watermark == 3
    assert bundle_source.event_store.calls == calls_before
