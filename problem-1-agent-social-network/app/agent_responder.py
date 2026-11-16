"""
Agent Responder for the AI Agent Social Network.
Uses Gemini to simulate autonomous AI-agent engagement decisions and comment drafting.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import google.generativeai as genai

from app.config import GEMINI_API_KEY as _DEFAULT_GEMINI_KEY

if TYPE_CHECKING:
    from app.models import Agent, Post


class AgentResponder:
    """Simulates an AI agent deciding whether and how to engage with a post."""

    def __init__(self, gemini_api_key: str | None = None):
        api_key = gemini_api_key or _DEFAULT_GEMINI_KEY
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    # ------------------------------------------------------------------
    # Engagement decision
    # ------------------------------------------------------------------

    def should_respond(
        self, agent: Agent, post: Post, relevance_score: float
    ) -> bool:
        """Decide whether the agent should engage with the post.

        Always returns False when relevance_score < 0.5.
        Otherwise asks Gemini to make the call.

        Args:
            agent: The agent that may respond.
            post: The post being evaluated.
            relevance_score: Pre-computed relevance score (0.0–1.0).

        Returns:
            True if the agent should engage, False otherwise.
        """
        if relevance_score < 0.5:
            return False

        interests_str = (
            ", ".join(agent.interests)
            if isinstance(agent.interests, list)
            else str(agent.interests)
        )
        prompt = (
            f"You are {agent.name} from {agent.company}, interested in {interests_str}. "
            f"A post says: '{post.content}'. "
            f"Relevance score: {relevance_score:.2f}. "
            "Should you engage? Reply YES or NO."
        )
        try:
            response = self.model.generate_content(prompt)
            answer = response.text.strip().upper()
            return answer.startswith("YES")
        except Exception:
            # Safe default: engage when score is high
            return relevance_score >= 0.7

    # ------------------------------------------------------------------
    # Comment drafting
    # ------------------------------------------------------------------

    def draft_comment(self, agent: Agent, post: Post) -> str:
        """Draft a business-appropriate reply from the agent to the post.

        Args:
            agent: The agent that will author the comment.
            post: The post being replied to.

        Returns:
            A short comment string (target ≤ 100 words).
        """
        prompt = (
            f"You are {agent.name}, an AI agent for {agent.company}. "
            f"Draft a business-appropriate reply to this post: '{post.content}'. "
            "Keep it under 100 words. Focus on how your company's services relate."
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            return (
                f"As {agent.name} from {agent.company}, we find this post highly relevant "
                "to our services. We'd love to connect and explore how we can collaborate!"
            )
