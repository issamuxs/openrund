"""Immutable trusted governance facts and deterministic schema checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePath
from typing import final

from openrund.contracts.capabilities import Capability, CapabilityAction
from openrund.contracts.commands import (
    AcceptedCommandDecision,
    CommandDecision,
    CommandDecisionTraceEntry,
    CreateActionOperation,
    DeferredCommandDecision,
    LegalityCriterion,
    LegalityCriterionResult,
    RejectedCommandDecision,
)
from openrund.contracts.content import (
    ArtifactReference,
    Content,
    Mutation,
    MutationOperationKind,
    MutationReversibility,
)
from openrund.contracts.events import (
    ApprovalWaitCreatedPayload,
    ApprovalWaitResolvedPayload,
)
from openrund.contracts.ids import ArtifactId, CapabilityId, WaitId
from openrund.contracts.json import (
    MISSING,
    JsonArray,
    JsonObject,
    JsonValue,
    MissingType,
    freeze_json,
)
from openrund.errors import ValidationError
from openrund.paths import LocalPath, PortablePath
from openrund.views import CompleteViewReplay
from openrund.views._model import RunViewBundle

_SCHEMA_KEYWORDS = frozenset(
    {
        "$schema",
        "title",
        "description",
        "type",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "enum",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "maxItems",
    }
)
_SCHEMA_TYPES = frozenset({"object", "array", "string", "number", "integer", "boolean", "null"})


@final
@dataclass(frozen=True, slots=True, kw_only=True)
class GovernanceContext:
    """Trusted assembly facts combined with durable per-Run governance."""

    capabilities: tuple[Capability, ...] = ()
    workspace_roots: tuple[LocalPath, ...] = ()
    tenant_id: str | MissingType | None = MISSING
    security_context: JsonObject | MissingType | None = MISSING

    def __post_init__(self) -> None:
        try:
            capabilities = tuple(self.capabilities)
            roots = tuple(self.workspace_roots)
        except TypeError as error:
            raise ValidationError(code="governance_context_invalid") from error
        if any(not isinstance(item, Capability) for item in capabilities):
            raise ValidationError(code="governance_capabilities_invalid")
        if len({item.capability_id for item in capabilities}) != len(capabilities):
            raise ValidationError(code="governance_capability_duplicate")
        if any(
            not isinstance(item, LocalPath)
            or not item.path.is_absolute()
            or ".." in item.path.parts
            for item in roots
        ):
            raise ValidationError(code="governance_workspace_roots_invalid")
        if len({item.raw for item in roots}) != len(roots):
            raise ValidationError(code="governance_workspace_root_duplicate")
        if self.tenant_id not in (MISSING, None) and (
            not isinstance(self.tenant_id, str) or self.tenant_id == ""
        ):
            raise ValidationError(code="governance_tenant_invalid")
        frozen_security: JsonObject | MissingType | None = self.security_context
        if frozen_security not in (MISSING, None):
            candidate = freeze_json(frozen_security)
            if not isinstance(candidate, JsonObject):
                raise ValidationError(code="governance_security_context_invalid")
            frozen_security = candidate
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "workspace_roots", roots)
        object.__setattr__(self, "security_context", frozen_security)

    def capability(self, capability_id: CapabilityId, /) -> Capability | None:
        return next(
            (item for item in self.capabilities if item.capability_id == capability_id),
            None,
        )

    def action(self, capability_id: CapabilityId, action_name: str, /) -> CapabilityAction | None:
        capability = self.capability(capability_id)
        if capability is None:
            return None
        return next((item for item in capability.actions if item.name == action_name), None)


def _schema_types(value: JsonValue | None, pointer: str, violations: list[str]) -> tuple[str, ...]:
    values: tuple[str, ...]
    if isinstance(value, str):
        values = (value,)
    elif isinstance(value, JsonArray) and all(isinstance(item, str) for item in value):
        values = tuple(item for item in value if isinstance(item, str))
    else:
        violations.append(f"{pointer}:schema_type_invalid")
        return ()
    if not values or any(item not in _SCHEMA_TYPES for item in values):
        violations.append(f"{pointer}:schema_type_invalid")
        return ()
    return values


def _matches_type(value: JsonValue, schema_type: str) -> bool:
    if schema_type == "object":
        return isinstance(value, JsonObject)
    if schema_type == "array":
        return isinstance(value, JsonArray)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    return value is None


def _integer_keyword(
    schema: JsonObject,
    name: str,
    pointer: str,
    violations: list[str],
) -> int | None:
    value = schema.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        violations.append(f"{pointer}:schema_{name}_invalid")
        return None
    return value


def _number_keyword(
    schema: JsonObject,
    name: str,
    pointer: str,
    violations: list[str],
) -> int | float | None:
    value = schema.get(name)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        violations.append(f"{pointer}:schema_{name}_invalid")
        return None
    return value


def _validate_schema_value(
    value: JsonValue,
    schema: JsonObject,
    pointer: str,
    violations: list[str],
) -> None:
    unknown = tuple(key for key in schema if key not in _SCHEMA_KEYWORDS)
    violations.extend(f"{pointer}:schema_keyword_unsupported:{key}" for key in unknown)

    declared_types = _schema_types(schema.get("type"), pointer, violations)
    if declared_types and not any(_matches_type(value, item) for item in declared_types):
        violations.append(f"{pointer}:type")
        return

    enum = schema.get("enum")
    if enum is not None:
        if not isinstance(enum, JsonArray) or not enum:
            violations.append(f"{pointer}:schema_enum_invalid")
        elif value not in enum:
            violations.append(f"{pointer}:enum")

    if isinstance(value, JsonObject):
        required = schema.get("required")
        if required is not None:
            if not isinstance(required, JsonArray) or any(
                not isinstance(item, str) or item == "" for item in required
            ):
                violations.append(f"{pointer}:schema_required_invalid")
            else:
                violations.extend(
                    f"{pointer}.{item}:required" for item in required if item not in value
                )
        properties = schema.get("properties")
        if properties is not None and not isinstance(properties, JsonObject):
            violations.append(f"{pointer}:schema_properties_invalid")
            properties = None
        if isinstance(properties, JsonObject):
            for name, child_schema in properties.entries:
                if not isinstance(child_schema, JsonObject):
                    violations.append(f"{pointer}.{name}:schema_invalid")
                elif name in value:
                    _validate_schema_value(
                        value[name], child_schema, f"{pointer}.{name}", violations
                    )
        additional = schema.get("additionalProperties")
        known = frozenset(properties) if isinstance(properties, JsonObject) else frozenset()
        extras = tuple(name for name in value if name not in known)
        if additional is False:
            violations.extend(f"{pointer}.{name}:additional_property" for name in extras)
        elif isinstance(additional, JsonObject):
            for name in extras:
                _validate_schema_value(value[name], additional, f"{pointer}.{name}", violations)
        elif additional not in (None, True):
            violations.append(f"{pointer}:schema_additional_properties_invalid")

    if isinstance(value, JsonArray):
        minimum = _integer_keyword(schema, "minItems", pointer, violations)
        maximum = _integer_keyword(schema, "maxItems", pointer, violations)
        if minimum is not None and len(value) < minimum:
            violations.append(f"{pointer}:min_items")
        if maximum is not None and len(value) > maximum:
            violations.append(f"{pointer}:max_items")
        items = schema.get("items")
        if items is not None:
            if not isinstance(items, JsonObject):
                violations.append(f"{pointer}:schema_items_invalid")
            else:
                for index, item in enumerate(value):
                    _validate_schema_value(item, items, f"{pointer}[{index}]", violations)

    if isinstance(value, str):
        minimum = _integer_keyword(schema, "minLength", pointer, violations)
        maximum = _integer_keyword(schema, "maxLength", pointer, violations)
        if minimum is not None and len(value) < minimum:
            violations.append(f"{pointer}:min_length")
        if maximum is not None and len(value) > maximum:
            violations.append(f"{pointer}:max_length")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum_number = _number_keyword(schema, "minimum", pointer, violations)
        maximum_number = _number_keyword(schema, "maximum", pointer, violations)
        if minimum_number is not None and value < minimum_number:
            violations.append(f"{pointer}:minimum")
        if maximum_number is not None and value > maximum_number:
            violations.append(f"{pointer}:maximum")


def schema_violations(value: JsonValue, schema: JsonObject, /) -> tuple[str, ...]:
    """Return stable fail-closed schema violations for one frozen JSON value."""

    if not isinstance(schema, JsonObject):
        raise TypeError("governance_schema_invalid")
    violations: list[str] = []
    _validate_schema_value(value, schema, "$", violations)
    return tuple(violations)


_KNOWN_POLICY_KINDS = frozenset(
    {
        "allow",
        "deny_capability",
        "deny_capability_action",
        "require_approval_for_capability_action",
        "require_approval_for_mutation",
    }
)
_ROOT_FIELDS = frozenset(
    {
        "mount",
        "toMount",
        "to_mount",
        "targetMount",
        "target_mount",
        "cwdMount",
        "cwd_mount",
        "repoMount",
        "repo_mount",
        "writableRoot",
        "writable_root",
    }
)
_ROOT_LIST_FIELDS = frozenset(
    {"roots", "workspaceRoots", "workspace_roots", "writableRoots", "writable_roots"}
)
_PATH_FIELDS = frozenset(
    {
        "path",
        "toPath",
        "to_path",
        "target",
        "targetPath",
        "target_path",
        "cwdPath",
        "cwd_path",
        "repoPath",
        "repo_path",
    }
)


def _entry(
    criterion: LegalityCriterion,
    result: LegalityCriterionResult,
    reason: str,
    *related: str,
) -> CommandDecisionTraceEntry:
    return CommandDecisionTraceEntry(
        criterion=criterion,
        result=result,
        reason=reason,
        related_entity_ids=related,
    )


def _reject_action(
    trace: list[CommandDecisionTraceEntry],
    criterion: LegalityCriterion,
    reason: str,
    *related: str,
) -> RejectedCommandDecision:
    trace.append(_entry(criterion, LegalityCriterionResult.FAIL, reason, *related))
    return RejectedCommandDecision(reason=reason, trace=tuple(trace))


def _pass(
    trace: list[CommandDecisionTraceEntry],
    criterion: LegalityCriterion,
    reason: str,
    *related: str,
) -> None:
    trace.append(_entry(criterion, LegalityCriterionResult.PASS, reason, *related))


def _object(value: object) -> JsonObject | None:
    return value if isinstance(value, JsonObject) else None


def _strings(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, JsonArray) or any(not isinstance(item, str) for item in value):
        return None
    return tuple(item for item in value if isinstance(item, str))


def _action_input(operation: CreateActionOperation) -> JsonObject:
    return (
        operation.input.data
        if isinstance(operation.input.data, JsonObject)
        else JsonObject(entries=())
    )


def _walk_scope_values(value: JsonValue) -> tuple[tuple[str, str], ...]:
    found: list[tuple[str, str]] = []
    if isinstance(value, JsonObject):
        for key, child in value.entries:
            if key in _ROOT_FIELDS and isinstance(child, str):
                found.append(("root", child))
            elif key in _ROOT_LIST_FIELDS:
                strings = _strings(child)
                if strings is not None:
                    found.extend(("root", item) for item in strings)
            elif key in _PATH_FIELDS and isinstance(child, str):
                found.append(("path", child))
            found.extend(_walk_scope_values(child))
    elif isinstance(value, JsonArray):
        for child in value:
            found.extend(_walk_scope_values(child))
    return tuple(found)


def _declared_roots(value: JsonObject) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for kind, item in _walk_scope_values(value) if kind == "root"))


def _constraint_roots(constraints: JsonObject | MissingType | None) -> tuple[str, ...] | None:
    if not isinstance(constraints, JsonObject):
        return None
    roots: list[str] = []
    declared = False
    for name in _ROOT_LIST_FIELDS:
        if name not in constraints:
            continue
        declared = True
        values = _strings(constraints[name])
        if values is None:
            return ()
        roots.extend(values)
    return tuple(dict.fromkeys(roots)) if declared else None


def _absolute_contained(path: str, roots: tuple[LocalPath, ...]) -> bool:
    if "\x00" in path or "\\" in path:
        return False
    candidate = PurePath(path)
    if not candidate.is_absolute():
        try:
            PortablePath(value=path)
        except ValidationError:
            return False
        return bool(roots)
    if ".." in candidate.parts:
        return False
    for root in roots:
        try:
            candidate.relative_to(root.path)
        except ValueError:
            continue
        return True
    return False


def _scope_violation(
    value: JsonObject,
    constraints: JsonObject | MissingType | None,
    context: GovernanceContext,
) -> str | None:
    allowed = _constraint_roots(constraints)
    if allowed == ():
        return "authority_scope_invalid"
    for kind, candidate in _walk_scope_values(value):
        if candidate == "":
            return "resource_scope_empty"
        if kind == "root" and allowed is not None and candidate not in allowed:
            return "resource_scope_unauthorized"
        if not _absolute_contained(candidate, context.workspace_roots):
            return "resource_scope_escape"
    return None


def _constraint_actions(constraints: JsonObject | MissingType | None) -> tuple[str, ...] | None:
    if not isinstance(constraints, JsonObject) or "actions" not in constraints:
        return None
    return _strings(constraints["actions"])


def _matches_rule(rule: JsonObject, operation: CreateActionOperation) -> bool:
    config = _object(rule.get("config"))
    if config is None:
        config = rule
    capability = config.get("capabilityID", config.get("capability_id"))
    action = config.get("actionName", config.get("action_name"))
    return (capability is None or capability == operation.capability_id.value) and (
        action is None or action == operation.action_name
    )


def _constraint_match(
    constraints: JsonObject | MissingType | None,
    context: GovernanceContext,
) -> tuple[LegalityCriterion, str] | None:
    if not isinstance(constraints, JsonObject):
        return None
    tenant = constraints.get("tenantId", constraints.get("tenant_id"))
    if tenant is not None and tenant != context.tenant_id:
        return LegalityCriterion.TENANT_SCOPE, "tenant_scope_mismatch"
    security = _object(constraints.get("securityContext", constraints.get("security_context")))
    if security is not None:
        actual = context.security_context
        if not isinstance(actual, JsonObject) or any(
            actual.get(key) != value for key, value in security.entries
        ):
            return LegalityCriterion.AUTHORITY, "security_context_mismatch"
    return None


def _content_json(content: Content | MissingType | None) -> JsonValue:
    if not isinstance(content, Content):
        return None
    value: dict[str, object] = {
        "artifactRefs": tuple(
            {
                "artifactId": reference.artifact_id.value,
                **({"kind": reference.kind} if isinstance(reference.kind, str) else {}),
                **({"preview": reference.preview} if isinstance(reference.preview, str) else {}),
                **(
                    {"metadata": reference.metadata}
                    if isinstance(reference.metadata, JsonObject)
                    else {}
                ),
            }
            for reference in content.artifact_refs
        ),
        "artifactIds": tuple(item.value for item in content.artifact_ids),
    }
    if content.preview is not MISSING:
        value["preview"] = content.preview
    if content.data is not MISSING:
        value["data"] = content.data
    if content.metadata is not MISSING:
        value["metadata"] = content.metadata
    return freeze_json(value)


def _content_from_json(value: JsonValue | None) -> Content | MissingType | None:
    if value is None:
        return MISSING
    if not isinstance(value, JsonObject):
        raise ValidationError(code="approval_content_invalid")
    raw_refs = value.get("artifactRefs")
    raw_ids = value.get("artifactIds")
    if not isinstance(raw_refs, JsonArray) or not isinstance(raw_ids, JsonArray):
        raise ValidationError(code="approval_content_invalid")
    refs: list[ArtifactReference] = []

    def optional_text(source: JsonObject, key: str) -> str | MissingType | None:
        raw = source.get(key, MISSING)
        if raw in (MISSING, None) or isinstance(raw, str):
            return raw
        raise ValidationError(code="approval_content_invalid")

    def optional_object(source: JsonObject, key: str) -> JsonObject | MissingType | None:
        raw = source.get(key, MISSING)
        if raw in (MISSING, None) or isinstance(raw, JsonObject):
            return raw
        raise ValidationError(code="approval_content_invalid")

    for raw_ref in raw_refs:
        if not isinstance(raw_ref, JsonObject) or not isinstance(raw_ref.get("artifactId"), str):
            raise ValidationError(code="approval_content_invalid")
        artifact_id = raw_ref["artifactId"]
        assert isinstance(artifact_id, str)
        refs.append(
            ArtifactReference(
                artifact_id=ArtifactId(value=artifact_id),
                kind=optional_text(raw_ref, "kind"),
                preview=optional_text(raw_ref, "preview"),
                metadata=optional_object(raw_ref, "metadata"),
            )
        )
    if any(not isinstance(item, str) for item in raw_ids):
        raise ValidationError(code="approval_content_invalid")
    return Content(
        preview=optional_text(value, "preview"),
        data=optional_object(value, "data"),
        artifact_refs=tuple(refs),
        artifact_ids=tuple(ArtifactId(value=item) for item in raw_ids if isinstance(item, str)),
        metadata=optional_object(value, "metadata"),
    )


def _mutation_json(mutation: Mutation | MissingType | None) -> JsonValue:
    if not isinstance(mutation, Mutation):
        return None
    value: dict[str, object] = {
        "affectedResources": mutation.affected_resources,
        "operationKind": mutation.operation_kind.value,
    }
    if isinstance(mutation.reversibility, MutationReversibility):
        value["reversibility"] = mutation.reversibility.value
    if isinstance(mutation.metadata, JsonObject):
        value["metadata"] = mutation.metadata
    if mutation.preview is not MISSING:
        value["preview"] = _content_json(mutation.preview)
    if mutation.check_plan is not MISSING:
        value["checkPlan"] = _content_json(mutation.check_plan)
    return freeze_json(value)


def _mutation_from_json(value: JsonValue | None) -> Mutation | MissingType | None:
    if value is None:
        return MISSING
    if not isinstance(value, JsonObject):
        raise ValidationError(code="approval_mutation_invalid")
    resources = value.get("affectedResources")
    operation_kind = value.get("operationKind")
    if not isinstance(resources, JsonArray) or any(
        not isinstance(item, JsonObject) for item in resources
    ):
        raise ValidationError(code="approval_mutation_invalid")
    if not isinstance(operation_kind, str):
        raise ValidationError(code="approval_mutation_invalid")
    reversibility = value.get("reversibility")
    raw_metadata = value.get("metadata")
    metadata = raw_metadata if isinstance(raw_metadata, JsonObject) else MISSING
    preview = _content_from_json(value.get("preview")) if "preview" in value else MISSING
    check_plan = _content_from_json(value.get("checkPlan")) if "checkPlan" in value else MISSING
    return Mutation(
        affected_resources=tuple(item for item in resources if isinstance(item, JsonObject)),
        operation_kind=MutationOperationKind(operation_kind),
        reversibility=(
            MutationReversibility(reversibility) if isinstance(reversibility, str) else MISSING
        ),
        preview=preview,
        check_plan=check_plan,
        metadata=metadata,
    )


def evaluate_governed_action(
    operation: CreateActionOperation,
    replay: CompleteViewReplay[RunViewBundle],
    context: GovernanceContext,
    *,
    approval_wait_id: WaitId | None = None,
    approval_satisfied: bool = False,
) -> CommandDecision:
    """Evaluate a governed Action in one stable fail-closed order."""

    trace: list[CommandDecisionTraceEntry] = []
    capability = context.capability(operation.capability_id)
    if capability is None:
        return _reject_action(
            trace,
            LegalityCriterion.CAPABILITY_METADATA,
            "capability_not_registered",
            operation.capability_id.value,
        )
    definition = context.action(operation.capability_id, operation.action_name)
    if definition is None:
        return _reject_action(
            trace,
            LegalityCriterion.CAPABILITY_METADATA,
            "capability_action_not_registered",
            operation.capability_id.value,
            operation.action_name,
        )
    _pass(
        trace,
        LegalityCriterion.CAPABILITY_METADATA,
        "capability_action_registered",
        operation.capability_id.value,
        operation.action_name,
    )

    data = _action_input(operation)
    violations = schema_violations(data, definition.input_schema)
    if violations:
        return _reject_action(
            trace, LegalityCriterion.CAPABILITY_SCHEMA, "capability_input_invalid", *violations
        )
    _pass(trace, LegalityCriterion.CAPABILITY_SCHEMA, "capability_input_valid")

    grant = replay.views.run_status.capability_authority.get(operation.capability_id)
    if grant is None:
        return _reject_action(
            trace,
            LegalityCriterion.AUTHORITY,
            "capability_authority_missing",
            operation.capability_id.value,
        )
    actions = _constraint_actions(grant.payload.constraints)
    if actions is not None and (not actions or operation.action_name not in actions):
        return _reject_action(
            trace,
            LegalityCriterion.AUTHORITY,
            "capability_action_not_authorized",
            operation.action_name,
        )
    _pass(trace, LegalityCriterion.AUTHORITY, "capability_authority_active", grant.event_id.value)

    scope_error = _scope_violation(data, grant.payload.constraints, context)
    if scope_error is None and isinstance(operation.mutation, Mutation):
        for resource in operation.mutation.affected_resources:
            scope_error = _scope_violation(resource, grant.payload.constraints, context)
            if scope_error is not None:
                break
    if scope_error is not None:
        return _reject_action(trace, LegalityCriterion.RESOURCE_SCOPE, scope_error)
    _pass(trace, LegalityCriterion.RESOURCE_SCOPE, "resource_scope_allowed", *_declared_roots(data))

    run = replay.views.run_status.run
    if run is None or (
        run.creation.parent_run_id not in (MISSING, None)
        and run.creation.parent_run_id == run.run_id
    ):
        return _reject_action(
            trace, LegalityCriterion.DELEGATION_LINEAGE, "delegation_lineage_invalid"
        )
    constraints = grant.payload.constraints
    if isinstance(constraints, JsonObject):
        expected_root = constraints.get("rootId", constraints.get("root_id"))
        expected_parent = constraints.get("parentRunId", constraints.get("parent_run_id"))
        parent = run.creation.parent_run_id
        if expected_root is not None and expected_root != run.root_id.value:
            return _reject_action(
                trace, LegalityCriterion.DELEGATION_LINEAGE, "delegation_root_mismatch"
            )
        if expected_parent is not None and (
            not isinstance(parent, type(run.run_id)) or expected_parent != parent.value
        ):
            return _reject_action(
                trace, LegalityCriterion.DELEGATION_LINEAGE, "delegation_parent_mismatch"
            )
    _pass(
        trace, LegalityCriterion.DELEGATION_LINEAGE, "delegation_lineage_valid", run.root_id.value
    )

    maximum: JsonValue | None = (
        constraints.get("maxActions") if isinstance(constraints, JsonObject) else None
    )
    if maximum is not None:
        if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
            return _reject_action(trace, LegalityCriterion.BUDGET, "action_budget_invalid")
        if len(replay.views.action_status) >= maximum:
            return _reject_action(trace, LegalityCriterion.BUDGET, "action_budget_exhausted")
    _pass(trace, LegalityCriterion.BUDGET, "action_budget_available")

    authority_constraints = (
        constraints,
        *(entry.payload.constraints for entry in replay.views.run_status.policy_authority.values()),
    )
    for active_constraints in authority_constraints:
        tenant_mismatch = _constraint_match(active_constraints, context)
        if tenant_mismatch is not None:
            criterion, reason = tenant_mismatch
            return _reject_action(trace, criterion, reason)
    _pass(trace, LegalityCriterion.TENANT_SCOPE, "tenant_scope_valid")

    if operation.action_id in replay.views.action_status:
        return _reject_action(
            trace, LegalityCriterion.CONTRACT, "action_already_exists", operation.action_id.value
        )

    for entry in replay.views.run_status.policy_authority.values():
        rule = entry.payload.rule
        kind = rule.get("kind")
        if not isinstance(kind, str) or kind not in _KNOWN_POLICY_KINDS:
            return _reject_action(
                trace,
                LegalityCriterion.POLICY,
                "policy_rule_unsupported",
                entry.payload.rule_id.value,
            )
        if not _matches_rule(rule, operation):
            continue
        if kind in ("deny_capability", "deny_capability_action"):
            return _reject_action(
                trace, LegalityCriterion.POLICY, "policy_denied", entry.payload.rule_id.value
            )
        requires_approval = kind == "require_approval_for_capability_action" or (
            kind == "require_approval_for_mutation" and isinstance(operation.mutation, Mutation)
        )
        if requires_approval and not approval_satisfied:
            if approval_wait_id is None:
                return _reject_action(
                    trace, LegalityCriterion.POLICY, "approval_wait_factory_unavailable"
                )
            trace.append(
                _entry(
                    LegalityCriterion.POLICY,
                    LegalityCriterionResult.DEFER,
                    "policy_requires_approval",
                    entry.payload.rule_id.value,
                )
            )
            return DeferredCommandDecision(
                reason="policy_requires_approval", trace=tuple(trace), wait_ids=(approval_wait_id,)
            )
    _pass(trace, LegalityCriterion.POLICY, "policy_allowed")
    return AcceptedCommandDecision(trace=tuple(trace))


def approval_wait_payload(
    operation: CreateActionOperation,
    wait_id: WaitId,
    replay: CompleteViewReplay[RunViewBundle],
) -> ApprovalWaitCreatedPayload:
    """Capture the exact proposed Action and current policy facts for approval."""

    grant = replay.views.run_status.capability_authority[operation.capability_id]
    policies = tuple(
        {"ruleId": entry.payload.rule_id.value, "rule": entry.payload.rule}
        for entry in replay.views.run_status.policy_authority.values()
    )
    snapshot_data = freeze_json(
        {
            "authorityEventId": grant.event_id.value,
            "policies": policies,
            "mutation": _mutation_json(operation.mutation),
        }
    )
    assert isinstance(snapshot_data, JsonObject)
    snapshot = Content(data=snapshot_data)
    return ApprovalWaitCreatedPayload(
        wait_id=wait_id,
        action_id=operation.action_id,
        capability_id=operation.capability_id,
        action_name=operation.action_name,
        request_payload=operation.input,
        policy_snapshot=snapshot,
        target=f"capability:{operation.capability_id.value}.{operation.action_name}:{operation.action_id.value}",
        reason="policy_requires_approval",
    )


def approved_action_operation(
    wait_id: WaitId,
    replay: CompleteViewReplay[RunViewBundle],
) -> tuple[CreateActionOperation | None, str]:
    terminal = next(
        (item for item in replay.views.waits.all_terminal if item.wait_id == wait_id), None
    )
    if terminal is None or terminal.kind.value != "approval":
        return None, "approval_not_found"
    if (
        not isinstance(terminal.terminal, ApprovalWaitResolvedPayload)
        or terminal.terminal.decision != "approved"
    ):
        return None, "approval_not_approved"
    if terminal.request is None or not isinstance(
        terminal.request.request, ApprovalWaitCreatedPayload
    ):
        return None, "approval_request_missing"
    request = terminal.request.request
    data = terminal.terminal.approved_input
    source = request.request_payload
    approved_content = Content(
        preview=source.preview,
        data=data if isinstance(data, JsonObject) else source.data,
        artifact_refs=source.artifact_refs,
        artifact_ids=source.artifact_ids,
        metadata=source.metadata,
    )
    snapshot = request.policy_snapshot.data
    mutation_value = snapshot.get("mutation") if isinstance(snapshot, JsonObject) else None
    try:
        mutation = _mutation_from_json(mutation_value)
    except (ValidationError, ValueError):
        return None, "approval_request_invalid"
    return (
        CreateActionOperation(
            action_id=request.action_id,
            capability_id=request.capability_id,
            action_name=request.action_name,
            input=approved_content,
            mutation=mutation,
        ),
        "approval_action_ready",
    )


def validate_approval_revision(
    operation_input: JsonObject,
    request: ApprovalWaitCreatedPayload,
    context: GovernanceContext,
) -> tuple[bool, str, JsonObject | None]:
    definition = context.action(request.capability_id, request.action_name)
    if definition is None:
        return False, "capability_action_not_registered", None
    violations = schema_violations(operation_input, definition.input_schema)
    if violations:
        return False, "approved_input_schema_invalid", None
    original = request.request_payload.data
    declared = _declared_roots(original) if isinstance(original, JsonObject) else ()
    revised = _declared_roots(operation_input)
    if any(root not in declared for root in revised):
        return False, "approved_input_scope_widened", None
    if (
        _scope_violation(
            operation_input,
            JsonObject(entries=(("writableRoots", freeze_json(declared)),)),
            context,
        )
        is not None
    ):
        return False, "approved_input_scope_invalid", None
    evidence = freeze_json(
        {"schemaValid": True, "scopeValid": True, "declaredWritableRoots": declared}
    )
    assert isinstance(evidence, JsonObject)
    return True, "approved_input_valid", evidence
