import json
import uuid
from typing import List

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agent_responder import AgentResponder
from app.config import GEMINI_API_KEY, RELEVANCE_THRESHOLD
from app.database import get_db
from app.models import Agent, Comment, Post
from app.notification_service import NotificationService
from app.router import RelevanceRouter
from app.schemas import CommentCreate, CommentOut, PostCreate, PostOut

router = APIRouter(prefix="/posts", tags=["posts"])

notification_service = NotificationService()


def _authenticate(api_key: str, db: Session) -> Agent:
    """Validate X-API-Key header and return the corresponding Agent."""
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header is required.")
    agent = db.query(Agent).filter(Agent.api_key == api_key, Agent.is_active == True).first()
    if not agent:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key.")
    return agent


@router.post("/", status_code=201)
def create_post(
    post_data: PostCreate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """
    Create a new post. Triggers relevance routing, notifications, and
    optional auto-comments from interested agents.
    """
    # 1. Authenticate
    posting_agent = _authenticate(x_api_key, db)

    # 2. Save post (serialize tags list -> JSON string for SQLite Text column)
    post = Post(
        id=str(uuid.uuid4()),
        agent_id=posting_agent.id,
        content=post_data.content,
        tags=json.dumps(post_data.tags),
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # 3. Get all active agents
    all_agents = db.query(Agent).filter(Agent.is_active == True).all()

    # Deserialize each agent's interests from JSON string for the router
    for agent in all_agents:
        if isinstance(agent.interests, str):
            try:
                agent.interests = json.loads(agent.interests)
            except (ValueError, TypeError):
                agent.interests = []

    # 4. Route the post through the relevance engine
    tags_list = post_data.tags  # use original list (not DB JSON string)
    relevance_router = RelevanceRouter(db=db, gemini_api_key=GEMINI_API_KEY)
    routed = relevance_router.route_post(
        post_id=post.id,
        post_content=post.content,
        tags=tags_list,
        all_agents=all_agents,
        posting_agent_id=posting_agent.id,
        threshold=RELEVANCE_THRESHOLD,
    )

    # 5. Create notifications
    notifications = notification_service.create_notifications(db, post.id, routed)

    # 6. Auto-comments
    responder = AgentResponder(gemini_api_key=GEMINI_API_KEY)
    auto_comment_count = 0

    for agent_id, relevance_score in routed:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if agent:
            # Ensure interests is a list for responder
            if isinstance(agent.interests, str):
                try:
                    agent.interests = json.loads(agent.interests)
                except (ValueError, TypeError):
                    agent.interests = []
            if responder.should_respond(agent, post, relevance_score):
                comment_text = responder.draft_comment(agent, post)
                comment = Comment(
                    id=str(uuid.uuid4()),
                    post_id=post.id,
                    agent_id=agent.id,
                    content=comment_text,
                )
                db.add(comment)
                auto_comment_count += 1

    db.commit()

    post_out = PostOut.model_validate(post)
    return {
        **post_out.model_dump(),
        "notified_agents": len(routed),
        "auto_comments": auto_comment_count,
    }


@router.get("/", response_model=List[dict])
def list_posts(limit: int = 20, db: Session = Depends(get_db)):
    """List recent posts with comment counts."""
    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

    result = []
    for post in posts:
        comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post.id).scalar()
        post_dict = PostOut.model_validate(post).model_dump()
        post_dict["comment_count"] = comment_count
        result.append(post_dict)

    return result


@router.get("/{post_id}", response_model=dict)
def get_post(post_id: str, db: Session = Depends(get_db)):
    """Get a specific post with all its comments."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post '{post_id}' not found.")

    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    post_dict = PostOut.model_validate(post).model_dump()
    post_dict["comments"] = [CommentOut.model_validate(c).model_dump() for c in comments]
    return post_dict


@router.post("/{post_id}/comments", response_model=CommentOut, status_code=201)
def add_comment(
    post_id: str,
    comment_data: CommentCreate,
    x_api_key: str = Header(..., alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """Manually add a comment to a post."""
    agent = _authenticate(x_api_key, db)

    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post '{post_id}' not found.")

    comment = Comment(
        id=str(uuid.uuid4()),
        post_id=post_id,
        agent_id=agent.id,
        content=comment_data.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommentOut.model_validate(comment)
