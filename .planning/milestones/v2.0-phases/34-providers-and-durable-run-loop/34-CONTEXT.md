---
phase: 34-providers-and-durable-run-loop
created: 2026-08-05
source: autonomous-context
discuss_skipped: true
---

# Phase 34 Context

## Goal

Drive model interaction through provider-neutral, resource-safe async execution while preserving the Engine as the only authority boundary.

## Locked Decisions

- Provider output is an untrusted `ModelProposal`, never a Command decision or Event.
- OpenAI Responses, Anthropic Messages, and local OpenAI-compatible endpoints use direct async HTTP/SSE rather than vendor SDKs.
- The base package remains dependency-free; transport is implemented with the Python async standard library and remains injectable for deterministic tests.
- Credentials are explicit constructor inputs. Adapters do not read ambient environment variables.
- Remote bodies, credentials, URLs with userinfo, and parser exceptions never cross the safe error boundary.
- A durable loop records ModelCall start before I/O and exactly one completion, failure, or cancellation fact before returning.
- Provider, worker, storage, Engine, and loop lifetimes support explicit async context management and leave no background task or process behind.
- Live provider checks are opt-in and skipped without explicit configuration.
- CLI interaction is ordinary Phase 36 plan/test work. No graphical UI artifact applies.

## Scope

- Provider-neutral tool schemas and response normalization.
- Bounded async HTTP/1.1 response and SSE transport.
- OpenAI Responses and local-compatible adapters.
- Anthropic Messages adapter.
- Durable ModelCall loop and cancellation handling.
- Async lifecycle integration, package typing, docs, and release gates.

## Out of Scope

- Provider routing, retries across models, prompt management, and conversation policy.
- WebSockets, realtime audio, server-side tools, and vendor SDK wrappers.
- Automatic Action execution after a proposal is accepted.
- CLI commands and graphical UI specifications.
