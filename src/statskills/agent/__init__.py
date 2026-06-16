"""The agent layer: the LLM client, the CodeAct action protocol, and the loop.

A single-agent ReAct loop (plan -> write code -> execute -> observe -> iterate)
whose action space is executable Python (CodeAct). Model access goes through a
provider-agnostic LLM client (the EdenAI gateway or a local Ollama backend), built
by :func:`~statskills.agent.llm.build_llm`.
"""
