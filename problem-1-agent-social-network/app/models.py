"""
SQLAlchemy ORM models for the AI Agent Social Network.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent(Base):
    __tablename__ = "agents"

    id          = Column(String, primary_key=True, default=_uuid)
    name        = Column(String, nullable=False)
    company     = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # JSON list stored as text, e.g. '["nlp","finance"]'
    interests   = Column(Text, nullable=True)
    api_key     = Column(String, nullable=False, unique=True, index=True)
    created_at  = Column(DateTime(timezone=True), default=_now, nullable=False)
    is_active   = Column(Boolean, default=True, nullable=False)

    posts         = relationship("Post", back_populates="agent", cascade="all, delete-orphan")
    comments      = relationship("Comment", back_populates="agent", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="agent", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="agent", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agents_name", "name"),
        Index("ix_agents_company", "company"),
    )


# ---------------------------------------------------------------------------
# Post
# ---------------------------------------------------------------------------

class Post(Base):
    __tablename__ = "posts"

    id            = Column(String, primary_key=True, default=_uuid)
    agent_id      = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content       = Column(Text, nullable=False)
    # JSON list stored as text, e.g. '["ai","llm"]'
    tags          = Column(Text, nullable=True)
    # Arbitrary JSON metadata stored as text
    metadata_json = Column(Text, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=_now, nullable=False)

    agent         = relationship("Agent", back_populates="posts")
    comments      = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="post", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_posts_agent_id", "agent_id"),
        Index("ix_posts_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Comment
# ---------------------------------------------------------------------------

class Comment(Base):
    __tablename__ = "comments"

    id         = Column(String, primary_key=True, default=_uuid)
    post_id    = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    agent_id   = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    post  = relationship("Post", back_populates="comments")
    agent = relationship("Agent", back_populates="comments")

    __table_args__ = (
        Index("ix_comments_post_id", "post_id"),
        Index("ix_comments_agent_id", "agent_id"),
        Index("ix_comments_created_at", "created_at"),
    )


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class Subscription(Base):
    __tablename__ = "subscriptions"

    id         = Column(String, primary_key=True, default=_uuid)
    agent_id   = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    topic      = Column(String, nullable=False)
    weight     = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    agent = relationship("Agent", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_subscriptions_agent_id", "agent_id"),
        Index("ix_subscriptions_topic", "topic"),
        Index("ix_subscriptions_agent_topic", "agent_id", "topic", unique=True),
    )


# ---------------------------------------------------------------------------
# Notification
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id              = Column(String, primary_key=True, default=_uuid)
    post_id         = Column(String, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    agent_id        = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    relevance_score = Column(Float, nullable=False, default=0.0)
    is_read         = Column(Boolean, default=False, nullable=False)
    created_at      = Column(DateTime(timezone=True), default=_now, nullable=False)

    post     = relationship("Post", back_populates="notifications")
    agent    = relationship("Agent", back_populates="notifications")
    feedback = relationship("NotificationFeedback", back_populates="notification", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_notifications_agent_id", "agent_id"),
        Index("ix_notifications_post_id", "post_id"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_agent_read", "agent_id", "is_read"),
    )


# ---------------------------------------------------------------------------
# NotificationFeedback
# ---------------------------------------------------------------------------

class NotificationFeedback(Base):
    __tablename__ = "notification_feedback"

    id              = Column(String, primary_key=True, default=_uuid)
    notification_id = Column(String, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    did_comment     = Column(Boolean, default=False, nullable=False)
    created_at      = Column(DateTime(timezone=True), default=_now, nullable=False)

    notification = relationship("Notification", back_populates="feedback")

    __table_args__ = (
        Index("ix_notification_feedback_notification_id", "notification_id"),
    )
