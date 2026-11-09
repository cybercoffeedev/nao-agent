"""Agent package - AI logic, LLM, ASR and orchestration.

The public classes are imported lazily so that lightweight modules such as
``agent.llm`` and ``agent.response_parser`` can be imported without pulling in
the NAOqi-dependent robot package.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .agent import RobotAgent
    from .asr import WhisperASR
    from .llm import LLMManager

__all__ = ["LLMManager", "RobotAgent", "WhisperASR"]


def __getattr__(name: str) -> Any:
    """Resolve public classes on first access."""
    if name == "RobotAgent":
        from .agent import RobotAgent

        return RobotAgent
    if name == "LLMManager":
        from .llm import LLMManager

        return LLMManager
    if name == "WhisperASR":
        from .asr import WhisperASR

        return WhisperASR
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
