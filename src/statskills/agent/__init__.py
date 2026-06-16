"""The agent layer: the LLM client, the CodeAct action protocol, and the loop.

A single-agent ReAct loop (plan -> write code -> execute -> observe -> iterate)
whose action space is executable Python (CodeAct). Model access goes through the
provider-agnostic :class:`~statskills.agent.llm.LLMClient` (EdenAI gateway).
"""
