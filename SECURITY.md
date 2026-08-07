# Security policy

OpenRund governs consequential agent work, so integrity failures, authority
bypasses, path escapes, unsafe process execution, secret exposure, and
ambiguous external outcomes are security concerns.

## Supported release

Security fixes are provided for the current 2.0 release line. Use the newest
available patch release before reporting a problem.

## Reporting a vulnerability

Report vulnerabilities privately through the repository host's security
reporting channel. If that channel is unavailable, contact the maintainer
through a private channel before publishing details. Include the affected
version, a minimal reproduction, expected impact, and any containment steps.

Do not include live credentials, private data, or destructive payloads in a
report. Do not open a public issue until a coordinated disclosure is agreed.

## Security boundaries

- Only `RuntimeEngine` decides mutation legality and materializes canonical
  lifecycle Events.
- Providers and models produce inert proposals, never authority.
- Capability workers return bounded results; they cannot append Events or
  grant Authority.
- Filesystem, document, process, Git, Bundle, and Run-home paths are confined
  and fail closed on traversal, platform confusion, or symbolic-link escape.
- Process execution uses explicit executable bindings and argument vectors;
  shell evaluation is not used.
- Provider credentials are explicit constructor inputs and are never read from
  ambient environment variables by production code.
- Unknown external outcomes stay unknown until evidence-backed reconciliation.
- Bundle import and replay provide custody and explanation, not Authority.

The normal test suite is offline and must not require credentials or network
access. Live-provider checks are opt-in and must use dedicated test accounts.

