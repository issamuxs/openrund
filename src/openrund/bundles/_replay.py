"""Replay verified Bundle history into explanatory Views."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import final

from openrund.contracts.events import RuntimeEvent
from openrund.paths import PathInput
from openrund.views import RunViewBundle

from ._model import BundleManifest
from ._verify import load_verified_bundle


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class BundleReplay:
    bundle_path: Path
    manifest: BundleManifest
    events: tuple[RuntimeEvent, ...]
    views: RunViewBundle


def replay_bundle(bundle_path: PathInput) -> BundleReplay:
    verified = load_verified_bundle(bundle_path)
    return BundleReplay(
        bundle_path=verified.path,
        manifest=verified.manifest,
        events=verified.events,
        views=verified.views,
    )
