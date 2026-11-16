"""
Conversation state manager for tracking multi-turn interactions and follow-ups.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import time


@dataclass
class Message:
    role: str  # "user", "model", "system", "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_responses: Optional[List[Dict[str, Any]]] = None
    timestamp: float = field(default_factory=time.time)


class ConversationSession:
    """Maintains dialog context, system instructions, and tool outputs."""

    def __init__(self, system_instruction: str):
        self.system_instruction = system_instruction
        self.history: List[Message] = []
        # Cache of recently inspected hardware components to minimize duplicate commands
        self.cached_hardware_state: Dict[str, Any] = {}

    def add_user_message(self, content: str) -> Message:
        msg = Message(role="user", content=content)
        self.history.append(msg)
        return msg

    def add_model_message(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tool_responses: Optional[List[Dict[str, Any]]] = None,
    ) -> Message:
        msg = Message(
            role="model",
            content=content,
            tool_calls=tool_calls,
            tool_responses=tool_responses,
        )
        self.history.append(msg)
        return msg

    def update_cache(self, category: str, data: Any):
        self.cached_hardware_state[category] = data

    def clear(self):
        self.history.clear()
        self.cached_hardware_state.clear()

