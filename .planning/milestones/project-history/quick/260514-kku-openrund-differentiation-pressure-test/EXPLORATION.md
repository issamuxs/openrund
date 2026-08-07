# OpenRund Differentiation Pressure Test

## Verdict

OpenRund is not differentiated by permissions, approvals, waits, persistence,
tool control, sandboxing, human-in-the-loop, tracing, or replay. Those are now
normal harness/runtime features.

OpenRund has a plausible but narrow differentiation only if it becomes a
mutation-legality runtime: the primary semantic object is not tool execution,
workflow progress, or agent orchestration, but whether an attempted mutation is
allowed to become authoritative Run history.

This is a real wedge, but it is narrow, subtle, and fragile. It is not an
obvious company thesis or a broad OSS category by itself. It is a high-quality
systems/research artifact with a possible narrow OSS wedge if the legality
kernel is real, inspectable, replayable, and easy to understand.

The defensible wedge is:

```text
Operation -> Command -> CommandDecision -> Events -> Views / Receipts / Reports
```

If OpenRund cannot prove that this transition model is materially cleaner than
middleware, hooks, traces, and workflow state in adjacent harnesses, the project
should be treated as a learning project or a specialized research runtime, not a
general OSS framework.

OpenRund is definitely a learning project. The question is whether it is only a
learning project. The answer depends on whether the CommandDecision-centered
legality kernel proves useful beyond the demo.

## What The Harness Article Changes

The user-provided harness article could not be read directly from Substack in
this environment, but public harness summaries and adjacent articles make the
same point: modern harnesses wrap models with tool integration, context
management, state, permissions, guardrails, feedback loops, orchestration,
memory, and recovery.

That invalidates weak OpenRund claims:

- "We manage permissions" is not differentiated.
- "We support approvals" is not differentiated.
- "We persist state" is not differentiated.
- "We replay or resume" is not differentiated.
- "We have CLI explanations" is not differentiated unless those explanations
  expose canonical runtime legality, not traces.
- "We support waits and human input" is not differentiated.
- "We control tools" is not differentiated.

The article strengthens the skeptical position: harness quality is becoming the
main competition layer, and OpenRund cannot win by being another harness with a
stricter vocabulary.

The stronger honest claim is not "nobody else can solve this." A strong team
can reproduce much of the model with Temporal, LangGraph or Agents SDK,
middleware, an event store, and custom audit records. The better claim is:
when teams solve consequential agent governance well, they tend to converge
toward an OpenRund-like legality kernel. OpenRund attempts to make that kernel
explicit, coherent, and testable.

## Competitive Read

| System | Strong existing claim | Direct overlap with OpenRund | OpenRund gap or possible wedge |
|---|---|---|---|
| Temporal | Durable execution, replay, retries, timers, activities, failure recovery. | Run durability, replay, retries, long-running execution, child work. | Temporal is execution/workflow-first. OpenRund must be legality-first for model-proposed consequential mutation, not a lighter Temporal. |
| Kitaru | Open-source runtime for long-running Python agents with checkpoints, replay, waits, isolated execution, versioned deployments, tracked LLM calls. | Long-running agent execution, waits, replay, checkpoints, model-call tracking, resume. | This is the most dangerous overlap. OpenRund must differentiate through CommandDecision legality, unknown outcome reconciliation, completion legality, and delegated Authority, not long-running agent runtime. |
| OpenAI Agents SDK | Agents, tools, handoffs, guardrails, tracing. Tool guardrails can run around each custom function-tool invocation. | Tool control, guardrails, handoffs, traceable agent workflows. | OpenAI guardrails are powerful but are primarily guardrail/tool/workflow surfaces. OpenRund must make legality decisions replayable runtime facts, not only guardrail tripwires or spans. |
| Microsoft Agent Framework / AGT | Agents plus graph workflows, type-safe routing, middleware, telemetry, state management, checkpointing, human-in-the-loop. | Middleware, HITL, workflow orchestration, checkpointing, typed workflows, governance-adjacent enterprise surfaces. | Microsoft is broader and stronger for enterprise orchestration. OpenRund's only wedge is stricter mutation admission semantics and canonical legality artifacts. |
| LangChain Deep Agents | Harness with planning, filesystem, subagents, long-term memory, durable LangGraph runtime, permissions, human-in-the-loop, sandboxes. | Filesystem, subagents, memory, permissions, HITL, durable agent execution. | Deep Agents is a direct harness competitor. OpenRund must not compete on agent productivity; it must compete on legal transition semantics and auditability of consequential mutation. |

## Classification

Current classification:

```text
Learning project: yes.
Only a learning project: not necessarily.
Product startup: unproven.
Broad OSS framework: weak.
Systems/research artifact: strong.
Narrow OSS wedge: possible.
```

OpenRund should be evaluated first as a serious systems artifact. If the
artifact is sharp enough, it can become a narrow embedded runtime component.
It should not be treated as a general agent platform.

## Real Differentiation Candidate

The strongest claim is not:

```text
model -> tool call -> policy -> approval -> execution -> trace
```

The strongest claim is:

```text
attempted mutation -> Command -> CommandDecision -> Event materialization
```

In that model:

- A model output is untrusted input.
- A Command is the attempted mutation.
- A CommandDecision is authoritative legality evaluation.
- Events are canonical immutable runtime facts.
- Views, Receipts, Reports, and CLI output are derived.
- Workers and providers are non-authority adapters.
- Completion is a terminal legality decision, not final text.

This is narrower than "agent harness". It is closer to an event-sourced legality
kernel for consequential agent work.

## Where The Wedge Is Strongest

1. Completion legality

Harnesses can end when the agent loop stops, output guardrails pass, a workflow
finishes, or an approval path completes. OpenRund's stronger claim is that
terminal Run state is itself a governed mutation: `run.completed`,
`run.failed`, and `run.cancelled` require accepted Commands and contract
satisfaction.

This is meaningful if completion legality is explicit, testable, and exported.

2. Unknown outcomes and reconciliation

Harnesses usually model timeouts, retries, failures, and traces. OpenRund's
stronger claim is epistemic: the runtime can know that it does not know whether
a side effect happened. That uncertainty becomes `action.unknown`, blocks
completion when required, and must be reconciled through a Command linked to
evidence.

This is one of the clearest differentiators.

3. Approval is not legality

Harnesses often treat human approval as a gate. OpenRund's stronger claim is
that approval can authorize only a valid attempted mutation. Illegal resource
scope, missing Authority, schema failure, or lifecycle impossibility are
rejections, not approval prompts.

This remains valuable only if every approval-resume path revalidates schema,
Authority, policy, resource scope, and Wait state.

4. Delegated Authority attenuation

Harnesses support subagents and handoffs. OpenRund's stronger claim is that
Delegation is a contract that bounds Authority. A child Run cannot silently
inherit or expand parent Authority, and child terminal Events do not
automatically become parent terminal Events.

This could be strong, but only if implemented and tested beyond documentation.

5. Replayable legality, not trace replay

Harnesses trace what happened. OpenRund should replay why a transition was legal
or illegal from CommandDecisions, Events, Waits, Checks, Authority, Artifacts,
and Bundles.

This is differentiated only if the runtime can answer "why was this allowed?"
without unrelated logs or middleware state.

## Weak Or Non-Differentiating Areas

- Durable execution.
- Checkpoints.
- Waits as pauses.
- Human-in-the-loop.
- Policy hooks.
- Tool guardrails.
- Filesystem permissions.
- Sandboxes.
- Tracing.
- Context management.
- Subagents.
- CLI display.
- Provider abstraction.
- Artifact storage.

These are table stakes or already covered by adjacent systems.

## Strategic Decision

OpenRund should not position itself as an agent harness, workflow engine, or
permissions layer.

The only strategically coherent position is:

> OpenRund is a governed mutation runtime for consequential agent work.

That means:

- Optimize for mutation admission, legality, and terminal contracts.
- Treat execution, tools, model calls, providers, and CLI as subordinate
  surfaces.
- Keep the ontology small and concrete.
- Make every claim falsifiable from Events, Commands, CommandDecisions, Waits,
  Checks, Authority, Artifacts, and Bundles.
- Avoid competing on harness productivity until the legality kernel is clearly
  valuable.

## Kill Criteria

OpenRund is not worth pushing as an OSS framework if any of these remain true:

- CommandDecision is just internal metadata, not a first-class inspectable
  runtime surface.
- Non-model mutation paths bypass Commands.
- Completion can be decided by model text, CLI helpers, or demo logic.
- Unknown outcomes are treated as errors/retries rather than explicit runtime
  state.
- Reconciliation can happen without evidence and linkage to the unknown Event.
- Delegation is just subagent orchestration without Authority attenuation.
- CLI explanations are pretty traces rather than derived legality surfaces.
- Bundles transport history but not enough governance semantics to answer why
  transitions were legal.

If those issues are not solved, OpenRund becomes a semantics-heavy harness
experiment, not a differentiated runtime.

## Build Criteria

OpenRund is worth continuing if it can demonstrate all of the following in a
small MVP:

- Illegal mutation rejection records a rejected CommandDecision and creates no
  target lifecycle Events.
- Approval-required valid mutation defers with a Wait and revalidates after
  approval.
- Capability workers never create authoritative history.
- Unknown side-effect outcomes become runtime state and block completion.
- Reconciliation is Command-owned, evidence-linked, and additive.
- Completion is a Command-owned terminal legality decision.
- Delegated Runs operate under explicit Authority contracts.
- `.orun` Bundles replay enough governance history to explain legality.
- CLI output can answer "why allowed, denied, delayed, unknown, reconciled, or
  completed" from runtime artifacts.

## Product Implication

The README/control direction is mostly correct, but the bar should be harsher:

- Stop implying "runtime control" is enough.
- Say directly that harness primitives are not the differentiation.
- Make mutation legality the project center.
- Keep current docs only if tests and APIs continue to prove the Command path.

Recommended next action: Phase 20 should include a public-facing
"Differentiation Verdict" section. It should say OpenRund is differentiated only
as a governed mutation-legality runtime, and only to the extent the code proves
CommandDecision-centered authority across every mutation path.

Recommended finish line:

1. Keep the runtime ontology-clean and minimal.
2. Keep the governed coding demo as the proof case.
3. Make CLI proof surfaces boring, canonical, and hard to fake.
4. Add a small causality/governance UI only if it visualizes legality, not chat
   or generic observability.
5. Publish a technical manifesto or systems-style paper only after the code
   proves the kernel.

The UI, if built, should make this structure visible:

```text
Run
  -> Commands
  -> CommandDecisions
  -> Waits
  -> Actions
  -> Checks
  -> Evidence
  -> Unknown/Reconciled outcomes
  -> Completion legality
```

The intended reaction is not "this is an agent dashboard." It should be "this
is a legality debugger for agent mutations."

Do not spend months building a broad platform, generic productivity features,
or a LangChain/OpenAI/Kitaru competitor. Finish the legality kernel, prove it,
then decide whether there is enough pull to continue.

## Sources Consulted

- Harness overview: `https://www.generative.inc/harness-engineering-the-most-important-skill-in-the-agentic-ai-era`
- Harness overview: `https://atlan.com/know/what-is-an-agent-harness/`
- Temporal docs: `https://docs.temporal.io/`
- Kitaru docs: `https://kitaru.ai/docs`
- OpenAI Agents SDK guardrails: `https://openai.github.io/openai-agents-python/guardrails/`
- Microsoft Agent Framework overview: `https://learn.microsoft.com/en-us/agent-framework/overview/`
- LangChain Deep Agents overview: `https://docs.langchain.com/oss/python/deepagents/overview`
