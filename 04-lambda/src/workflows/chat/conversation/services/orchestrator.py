"""Conversation orchestrator for coordinating multiple agents."""

import logging
from typing import Any

import openai
from workflows.chat.conversation.config import config

logger = logging.getLogger(__name__)


class ConversationOrchestrator:
    """
    Orchestrates conversation flow by coordinating multiple agents.

    This is a simplified version adapted from wandering-athena's LangGraph-based
    orchestrator. It uses Pydantic AI patterns instead of LangGraph.
    """

    def __init__(self, llm_client: openai.AsyncOpenAI | None = None):
        """
        Initialize conversation orchestrator.

        Args:
            llm_client: Optional OpenAI client
        """
        self.llm_client = llm_client

    async def plan_response(
        self, user_message: str, voice_instructions: str, available_tools: list[str]
    ) -> dict[str, Any]:
        """
        Plan the response using LLM.

        Determines:
        - Whether to use tools
        - Which tools to use
        - Response strategy

        Args:
            user_message: User's message
            voice_instructions: Persona voice instructions
            available_tools: List of available tool names

        Returns:
            Plan dict with action, tools, and strategy
        """
        if not self.llm_client:
            # Fallback: simple response
            return {
                "action": "respond_directly",
                "tools": [],
                "strategy": "Provide a helpful response",
            }

        try:
            prompt = f"""You are a conversation orchestrator. Plan how to respond to the user's message.

User message: {user_message}

Persona context:
{voice_instructions}

Available tools: {", ".join(available_tools)}

Determine:
1. Action: "respond_directly", "use_memory", "search_knowledge", "use_calendar", or "multi_tool"
2. Tools to use (if any): List of tool names
3. Strategy: Brief description of response approach

Respond in format: action|tools|strategy
Example: search_knowledge|enhanced_search|Search knowledge base and provide answer"""

            response = await self.llm_client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            result = (
                response.choices[0].message.content
                or "respond_directly||Provide a helpful response"
            )
            parts = result.split("|")
            action = parts[0].strip() if len(parts) > 0 else "respond_directly"
            tools_str = parts[1].strip() if len(parts) > 1 else ""
            tools = [t.strip() for t in tools_str.split(",") if t.strip()] if tools_str else []
            strategy = parts[2].strip() if len(parts) > 2 else "Provide a helpful response"

            return {"action": action, "tools": tools, "strategy": strategy}
        except Exception as e:
            logger.warning(f"Error planning response: {e}")
            return {
                "action": "respond_directly",
                "tools": [],
                "strategy": "Provide a helpful response",
            }

    async def generate_response(
        self,
        user_message: str,
        voice_instructions: str,
        tool_results: dict[str, Any] | None = None,
        plan: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate final response using LLM.

        Args:
            user_message: User's message
            voice_instructions: Persona voice instructions
            tool_results: Results from tool execution (if any)
            plan: Response plan

        Returns:
            Generated response text
        """
        if not self.llm_client:
            return "I'm here to help, but I need LLM configuration to respond properly."

        try:
            prompt_parts = [
                f"User message: {user_message}",
                "",
                "Persona context:",
                voice_instructions,
            ]

            if plan:
                prompt_parts.append("")
                prompt_parts.append(
                    f"Response strategy: {plan.get('strategy', 'Provide a helpful response')}"
                )

            if tool_results:
                prompt_parts.append("")
                prompt_parts.append("Tool results:")
                for tool_name, result in tool_results.items():
                    prompt_parts.append(f"{tool_name}: {result}")

            prompt_parts.append("")
            prompt_parts.append(
                "Generate a helpful, natural response based on the persona context and any tool results."
            )

            prompt = "\n".join(prompt_parts)

            response = await self.llm_client.chat.completions.create(
                model=config.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )

            return (
                response.choices[0].message.content
                or "I apologize, but I couldn't generate a response."
            )
        except Exception:
            logger.exception("Error generating response")
            return "I apologize, but I encountered an error generating a response."
