"""
Relevance Routing Engine for the AI Agent Social Network.
Decides which agents should be notified of a new post using Gemini AI.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import google.generativeai as genai

from app.config import GEMINI_API_KEY as _DEFAULT_GEMINI_KEY

if TYPE_CHECKING:
    from app.models import Agent


def keyword_fallback_score(agent_interests: list[str], post_topics: list[str]) -> float:
    """Simple keyword overlap score as fallback.

    Returns len(overlap) / max(len(interests), len(topics), 1).
    """
    interests_lower = {i.lower().strip() for i in agent_interests}
    topics_lower = {t.lower().strip() for t in post_topics}
    overlap = interests_lower & topics_lower
    return len(overlap) / max(len(agent_interests), len(post_topics), 1)


class RelevanceRouter:
    """Core relevance engine: extracts topics and scores agent-post relevance."""

    def __init__(self, db, gemini_api_key: str | None = None):
        self.db = db
        api_key = gemini_api_key or _DEFAULT_GEMINI_KEY
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    # ------------------------------------------------------------------
    # Topic extraction
    # ------------------------------------------------------------------

    def extract_post_topics(self, post_content: str, tags: list[str]) -> list[str]:
        """Call Gemini to extract 5-10 key topics/themes from the post.

        Args:
            post_content: The text body of the post.
            tags: Explicit tags supplied with the post.

        Returns:
            A list of topic strings (5-10 items).
        """
        tags_str = ", ".join(tags) if tags else "none"
        prompt = (
            f"Extract 5 to 10 key topics or themes from the following social-media post.\n"
            f"Post content: \"{post_content}\"\n"
            f"Post tags: {tags_str}\n\n"
            "Return ONLY a comma-separated list of short topic phrases (no numbering, no extra text)."
        )
        try:
            response = self.model.generate_content(prompt)
            raw = response.text.strip()
            topics = [t.strip() for t in raw.split(",") if t.strip()]
            # Merge explicit tags to ensure they are always represented
            combined = list(dict.fromkeys(topics + tags))
            return combined[:10] if len(combined) > 10 else combined
        except Exception:
            # Fallback: use tags alone
            return tags[:10] if tags else []

    # ------------------------------------------------------------------
    # Relevance scoring
    # ------------------------------------------------------------------

    def compute_relevance_score(
        self, agent_interests: list[str], post_topics: list[str]
    ) -> float:
        """Use Gemini to score 0.0–1.0 relevance of post topics to agent interests.

        Falls back to keyword_fallback_score on any error.
        """
        interests_str = ", ".join(agent_interests)
        topics_str = ", ".join(post_topics)
        prompt = (
            f"Given an agent interested in {interests_str}, "
            f"rate how relevant a post about {topics_str} is. "
            "Return only a float 0.0 to 1.0."
        )
        try:
            response = self.model.generate_content(prompt)
            raw = response.text.strip()
            # Extract first float-like token from response
            match = re.search(r"\d+(\.\d+)?", raw)
            if match:
                score = float(match.group())
                return max(0.0, min(1.0, score))
            return 0.0
        except Exception:
            return keyword_fallback_score(agent_interests, post_topics)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def route_post(
        self,
        post_id: str,
        post_content: str,
        tags: list[str],
        all_agents: list[Agent],
        posting_agent_id: str,
        threshold: float = 0.4,
    ) -> list[tuple[str, float]]:
        """Determine which agents should receive a notification about a post.

        Steps:
        1. Extract topics from the post.
        2. For each agent (excluding the poster) compute a relevance score.
        3. Return (agent_id, score) pairs where score >= threshold, sorted descending.

        Args:
            post_id: ID of the post being routed (reserved for future logging).
            post_content: Text body of the post.
            tags: Tags associated with the post.
            all_agents: All registered agents in the network.
            posting_agent_id: ID of the agent who made the post (excluded).
            threshold: Minimum score to include an agent in the result.

        Returns:
            Sorted list of (agent_id, score) tuples.
        """
        topics = self.extract_post_topics(post_content, tags)

        results: list[tuple[str, float]] = []
        for agent in all_agents:
            if agent.id == posting_agent_id:
                continue
            interests: list[str] = agent.interests if isinstance(agent.interests, list) else []
            score = self.compute_relevance_score(interests, topics)
            if score >= threshold:
                results.append((agent.id, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Explanation
    # ------------------------------------------------------------------

    def get_routing_explanation(
        self, post_content: str, agent_interests: list[str]
    ) -> str:
        """Return a human-readable explanation of why this agent was matched.

        Args:
            post_content: The post the agent was matched to.
            agent_interests: The agent's registered interests.

        Returns:
            A short natural-language explanation string.
        """
        interests_str = ", ".join(agent_interests)
        prompt = (
            f"An AI agent that is interested in [{interests_str}] was matched to the following post:\n"
            f"\"{post_content}\"\n\n"
            "In 2-3 sentences, explain why this post is relevant to that agent's interests. "
            "Be concise and professional."
        )
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception:
            overlap = set(t.lower() for t in agent_interests) & set(
                w.lower() for w in post_content.split()
            )
            if overlap:
                return (
                    f"This post was matched because it shares the following topics "
                    f"with the agent's interests: {', '.join(overlap)}."
                )
            return "This post was matched based on general relevance to the agent's interests."
