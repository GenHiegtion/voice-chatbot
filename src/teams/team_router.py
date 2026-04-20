"""Shared utilities for team-level router nodes."""

import asyncio
import json
import logging
from collections.abc import Iterable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage

from src.agents.state import AgentState

logger = logging.getLogger(__name__)


def _is_expected_provider_error(exc: Exception) -> bool:
    """Identify transient upstream/provider errors to keep logs concise."""
    name = type(exc).__name__
    if name in {"ResponseError", "ConnectError", "ReadTimeout", "TimeoutException"}:
        return True

    text = str(exc).lower()
    return any(token in text for token in ["status code: 500", "internal server error", "timeout"])


def _parse_router_json(content: str) -> tuple[str, str]:
    """Parse structured router output and return next target with direct response."""
    try:
        cleaned = content
        if "```json" in cleaned:
            cleaned = cleaned.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```", 1)[1].split("```", 1)[0]

        decision = json.loads(cleaned.strip())
        next_agent = str(decision.get("next", "FINISH"))
        direct_response = str(decision.get("response", ""))
        return next_agent, direct_response
    except (json.JSONDecodeError, IndexError, AttributeError, TypeError):
        return "FINISH", str(content)


def create_team_router_node(
    llm: BaseChatModel,
    *,
    system_prompt: str,
    valid_targets: Iterable[str],
    flow_name: str,
    fallback_message: str,
):
    """Create a reusable router node for coordinator/team orchestration."""
    allowed_targets = set(valid_targets)

    async def team_router_node(state: AgentState) -> dict:
        """Route input to the next node or answer directly."""
        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        session_id = state.get("session_id", "")
        user_preview = ""
        for msg in reversed(state["messages"]):
            if getattr(msg, "type", "") == "human" and getattr(msg, "content", ""):
                user_preview = " ".join(str(msg.content).split())[:160]
                break

        logger.info(
            "FLOW %s.start session_id=%s message=%s",
            flow_name,
            session_id,
            user_preview,
        )

        response = None
        for attempt in range(1, 3):
            try:
                response = await llm.ainvoke(messages)
                break
            except Exception as exc:
                logger.warning(
                    "FLOW %s.llm_failed session_id=%s attempt=%s",
                    flow_name,
                    session_id,
                    attempt,
                )
                if not _is_expected_provider_error(exc):
                    logger.debug(
                        "FLOW %s.llm_failed_details session_id=%s attempt=%s",
                        flow_name,
                        session_id,
                        attempt,
                        exc_info=True,
                    )
                if attempt < 2:
                    await asyncio.sleep(0.4 * attempt)

        if response is None:
            logger.error("FLOW %s.fallback session_id=%s", flow_name, session_id)
            return {
                "next_agent": "FINISH",
                "messages": [AIMessage(content=fallback_message)],
            }

        next_agent, direct_response = _parse_router_json(response.content)

        if next_agent not in allowed_targets:
            logger.warning(
                "FLOW %s.invalid_target session_id=%s invalid_target=%s fallback=FINISH",
                flow_name,
                session_id,
                next_agent,
            )
            next_agent = "FINISH"

        logger.info(
            "FLOW %s.route_decision session_id=%s next_agent=%s",
            flow_name,
            session_id,
            next_agent,
        )
        logger.info(
            "FLOW interaction.delegate session_id=%s from=%s to=%s",
            session_id,
            flow_name,
            "END" if next_agent == "FINISH" else next_agent,
        )

        result = {"next_agent": next_agent}
        if next_agent == "FINISH" and direct_response:
            logger.info(
                "FLOW %s.direct_response session_id=%s response_chars=%s",
                flow_name,
                session_id,
                len(direct_response),
            )
            result["messages"] = [AIMessage(content=direct_response)]
        return result

    return team_router_node
