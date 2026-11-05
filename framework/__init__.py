"""Enterprise self-healing Playwright automation framework."""

from framework.llm.prompt_config import LlmPromptOverride
from framework.wrapper.self_healing_page import SelfHealingPage

__all__ = ["LlmPromptOverride", "SelfHealingPage"]
