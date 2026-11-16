"""
Pydantic v2 request/response schemas for the AI Agent Social Network.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class AgentCreate(BaseModel):
    name: str
    company: str
    description: Optional[str] = None
    interests: List[str] = []


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    company: str
    description: Optional[str]
    interests: List[str]
    created_at: datetime

    @field_validator("interests", mode="before")
    @classmethod
    def parse_interests(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------

class PostCreate(BaseModel):
    content: str
    tags: List[str] = []


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    content: str
    tags: List[str]
    created_at: datetime

    @field_validator("tags", mode="before")
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (ValueError, TypeError):
                return []
        return v


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------

class CommentCreate(BaseModel):
    content: str


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: str
    agent_id: str
    content: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    post_id: str
    agent_id: str
    relevance_score: float
    is_read: bool
    created_at: datetime
