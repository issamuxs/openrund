"""Validated Capability registration, transport, and built-in execution boundaries."""

from openrund.capabilities._registry import (
    ActionTransportBinding,
    CapabilityRegistry,
    CapabilityRoute,
    RegisteredCapability,
)
from openrund.capabilities._runner import ActionRunner, ActionRunnerDependencies
from openrund.capabilities._sandbox import FilesystemMount, RootSandbox
from openrund.capabilities._transports import (
    InProcessTransport,
    StdioJsonRpcConfig,
    StdioJsonRpcTransport,
)
from openrund.capabilities.documents import DocumentsCapability
from openrund.capabilities.filesystem import FilesystemCapability
from openrund.capabilities.git import GitCapability, GitIdentity
from openrund.capabilities.process import (
    ProcessBinding,
    ProcessCapability,
    ProcessEnvironmentRule,
)

__all__ = [
    "ActionRunner",
    "ActionRunnerDependencies",
    "ActionTransportBinding",
    "CapabilityRegistry",
    "CapabilityRoute",
    "DocumentsCapability",
    "FilesystemCapability",
    "FilesystemMount",
    "GitCapability",
    "GitIdentity",
    "InProcessTransport",
    "ProcessBinding",
    "ProcessCapability",
    "ProcessEnvironmentRule",
    "RegisteredCapability",
    "RootSandbox",
    "StdioJsonRpcConfig",
    "StdioJsonRpcTransport",
]
