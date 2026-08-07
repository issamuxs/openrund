---
phase: 37-python-only-cutover-and-release
plan: "04"
status: complete
completed: 2026-08-04
requirements: [REL-02, REL-03]
commits: [025672c]
---

# Plan 37-04 Summary

Removed the quarantined executable oracle, retired package workspace,
non-Python tests, duplicate worker distribution, package-manager/build files,
generated dependency trees, and historical product-doc archive while retaining
the immutable compatibility fixture corpus and Git history.

Replaced the public example with a typed Python API script and installed-command
instructions. A repository fence now rejects removed roots, code suffixes, and
tool commands. The post-cutover suite passed with 971 tests and three opt-in
live-provider skips.

