"""Agent runtime modules.

Design spec Section 4.4:
- tool_registry: OpenAI tool schemas and obsolete alias rejection.
- tool_executor: Dispatches tool calls to service adapters with retries.
- agent_memory: Message history, milestones, and sanitized traces.
- agent_policy: Guardrail enforcement (ordering, limits, auto-flags).
- agent_runner: Iteration loop, model calls, and result compilation.
"""

from backend.app.agent.tool_registry import (
    CANONICAL_TOOL_NAMES,
    get_tool_schemas,
    validate_tool_name,
)
from backend.app.agent.tool_executor import ToolExecutor, ToolExecutionError
from backend.app.agent.agent_memory import AgentMemory
from backend.app.agent.agent_policy import AgentPolicy, PolicyDecision
from backend.app.agent.agent_runner import AgentRunner, AgentResult

__all__ = [
    "CANONICAL_TOOL_NAMES",
    "get_tool_schemas",
    "validate_tool_name",
    "ToolExecutor",
    "ToolExecutionError",
    "AgentMemory",
    "AgentPolicy",
    "PolicyDecision",
    "AgentRunner",
    "AgentResult",
]
