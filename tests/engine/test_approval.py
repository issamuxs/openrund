from __future__ import annotations

import asyncio

from openrund._testing.memory import MemoryEventStore
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CommandOrigin,
    DeferredCommandDecision,
    GrantCapabilityAuthorityOperation,
    GrantPolicyAuthorityOperation,
    RejectedCommandDecision,
    ResolveApprovalOperation,
    ResumeApprovedActionOperation,
    RevokeCapabilityAuthorityOperation,
)
from openrund.contracts.events import (
    ActionCreatedPayload,
    ApprovalWaitResolvedPayload,
    CoreEventType,
)
from openrund.contracts.ids import CapabilityId, PolicyRuleId
from openrund.engine import EngineDependencies, RuntimeEngine
from tests.engine.test_governance import (
    RUN_ID,
    _action,
    _command,
    _configured,
    _json,
    _seed,
)


def _grant_governance(engine: RuntimeEngine) -> None:
    capability = asyncio.run(
        engine.submit(
            _command(
                "grant-capability",
                GrantCapabilityAuthorityOperation(
                    capability_id=CapabilityId(value="filesystem"),
                    constraints=_json(
                        {
                            "actions": ["write"],
                            "writableRoots": ["/workspace"],
                        }
                    ),
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    policy = asyncio.run(
        engine.submit(
            _command(
                "grant-policy",
                GrantPolicyAuthorityOperation(
                    rule_id=PolicyRuleId(value="writes-require-approval"),
                    rule=_json(
                        {
                            "kind": "require_approval_for_capability_action",
                            "config": {
                                "capabilityID": "filesystem",
                                "actionName": "write",
                            },
                        }
                    ),
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    assert isinstance(capability.decision, AcceptedCommandDecision)
    assert isinstance(policy.decision, AcceptedCommandDecision)


def test_approved_action_resumes_once_after_full_current_revalidation(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    _grant_governance(engine)

    proposal_command = _command("propose", _action("action_1"), origin=CommandOrigin.MODEL)
    proposed = asyncio.run(engine.submit(proposal_command))
    proposal_retry = asyncio.run(engine.submit(proposal_command))
    assert isinstance(proposed.decision, DeferredCommandDecision)
    assert proposal_retry == proposed
    wait_id = proposed.decision.wait_ids[0]

    approved = asyncio.run(
        engine.submit(
            _command(
                "approve",
                ResolveApprovalOperation(
                    wait_id=wait_id,
                    decision="approved",
                    approved_input=_json(
                        {
                            "path": "/workspace/final.md",
                            "content": "done",
                            "writableRoots": ["/workspace"],
                        }
                    ),
                    resolved_by="operator",
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    resumed_command = _command(
        "resume",
        ResumeApprovedActionOperation(wait_id=wait_id),
        origin=CommandOrigin.SYSTEM,
    )
    resumed = asyncio.run(engine.submit(resumed_command))
    identical_retry = asyncio.run(engine.submit(resumed_command))

    assert isinstance(approved.decision, AcceptedCommandDecision)
    assert isinstance(resumed.decision, AcceptedCommandDecision)
    assert identical_retry == resumed
    history = asyncio.run(event_store.read(RUN_ID))
    resolutions = tuple(
        event.payload
        for event in history.events
        if isinstance(event.payload, ApprovalWaitResolvedPayload)
    )
    actions = tuple(
        event.payload for event in history.events if isinstance(event.payload, ActionCreatedPayload)
    )
    assert len(resolutions) == 1
    validation = resolutions[0].approved_input_validation
    assert validation not in (None,)
    assert len(actions) == 1
    assert actions[0].input.data == _json(
        {
            "path": "/workspace/final.md",
            "content": "done",
            "writableRoots": ["/workspace"],
        }
    )
    assert not any(event.event_type is CoreEventType.ACTION_STARTED for event in history.events)


def test_revoked_authority_makes_approved_resume_stale(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    _grant_governance(engine)
    proposed = asyncio.run(
        engine.submit(_command("propose", _action("action_1"), origin=CommandOrigin.MODEL))
    )
    assert isinstance(proposed.decision, DeferredCommandDecision)
    wait_id = proposed.decision.wait_ids[0]
    approved = asyncio.run(
        engine.submit(
            _command(
                "approve",
                ResolveApprovalOperation(wait_id=wait_id, decision="approved"),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    revoked = asyncio.run(
        engine.submit(
            _command(
                "revoke",
                RevokeCapabilityAuthorityOperation(capability_id=CapabilityId(value="filesystem")),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    resumed = asyncio.run(
        engine.submit(
            _command(
                "resume",
                ResumeApprovedActionOperation(wait_id=wait_id),
                origin=CommandOrigin.SYSTEM,
            )
        )
    )

    assert isinstance(approved.decision, AcceptedCommandDecision)
    assert isinstance(revoked.decision, AcceptedCommandDecision)
    assert isinstance(resumed.decision, RejectedCommandDecision)
    assert resumed.decision.reason == "capability_authority_missing"
    history = asyncio.run(event_store.read(RUN_ID))
    assert not any(isinstance(event.payload, ActionCreatedPayload) for event in history.events)


def test_denial_and_scope_widening_cannot_resume(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    _grant_governance(engine)
    first = asyncio.run(
        engine.submit(_command("first", _action("action_1"), origin=CommandOrigin.MODEL))
    )
    second = asyncio.run(
        engine.submit(_command("second", _action("action_2"), origin=CommandOrigin.MODEL))
    )
    assert isinstance(first.decision, DeferredCommandDecision)
    assert isinstance(second.decision, DeferredCommandDecision)

    denied = asyncio.run(
        engine.submit(
            _command(
                "deny",
                ResolveApprovalOperation(
                    wait_id=first.decision.wait_ids[0],
                    decision="denied",
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )
    denied_resume = asyncio.run(
        engine.submit(
            _command(
                "resume-denied",
                ResumeApprovedActionOperation(wait_id=first.decision.wait_ids[0]),
                origin=CommandOrigin.SYSTEM,
            )
        )
    )
    widened = asyncio.run(
        engine.submit(
            _command(
                "widen",
                ResolveApprovalOperation(
                    wait_id=second.decision.wait_ids[0],
                    decision="approved",
                    approved_input=_json(
                        {
                            "path": "/outside/report.md",
                            "content": "done",
                            "writableRoots": ["/workspace", "/outside"],
                        }
                    ),
                ),
                origin=CommandOrigin.OPERATOR,
            )
        )
    )

    assert isinstance(denied.decision, AcceptedCommandDecision)
    assert isinstance(denied_resume.decision, RejectedCommandDecision)
    assert denied_resume.decision.reason == "approval_not_approved"
    assert isinstance(widened.decision, RejectedCommandDecision)
    assert widened.decision.reason == "approved_input_scope_widened"


def test_model_cannot_approve_its_own_deferred_action(
    engine_dependencies: EngineDependencies,
    event_store: MemoryEventStore,
) -> None:
    _seed(event_store)
    engine = RuntimeEngine(_configured(engine_dependencies))
    _grant_governance(engine)
    proposed = asyncio.run(
        engine.submit(_command("propose", _action("action_1"), origin=CommandOrigin.MODEL))
    )
    assert isinstance(proposed.decision, DeferredCommandDecision)

    self_approved = asyncio.run(
        engine.submit(
            _command(
                "self-approve",
                ResolveApprovalOperation(
                    wait_id=proposed.decision.wait_ids[0],
                    decision="approved",
                ),
                origin=CommandOrigin.MODEL,
            )
        )
    )

    assert isinstance(self_approved.decision, RejectedCommandDecision)
    assert self_approved.decision.reason == "coordination_origin_forbidden"
    history = asyncio.run(event_store.read(RUN_ID))
    assert not any(
        isinstance(event.payload, ApprovalWaitResolvedPayload) for event in history.events
    )
