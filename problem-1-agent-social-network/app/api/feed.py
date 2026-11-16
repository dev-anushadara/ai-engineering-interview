from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, Comment, Notification, Post
from app.schemas import CommentOut, PostOut

router = APIRouter(prefix="/feed", tags=["feed"])


def _post_with_comments(post: Post, db: Session) -> dict:
    """Serialize a post together with all its comments."""
    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post.id)
        .order_by(Comment.created_at.asc())
        .all()
    )
    post_dict = PostOut.model_validate(post).model_dump()
    post_dict["comments"] = [CommentOut.model_validate(c).model_dump() for c in comments]
    post_dict["comment_count"] = len(comments)
    return post_dict


@router.get("/", response_model=List[dict])
def global_feed(limit: int = 20, db: Session = Depends(get_db)):
    """
    Global feed: most recent posts sorted by activity
    (number of comments descending, then by created_at descending).
    """
    # Subquery: comment count per post
    comment_counts = (
        db.query(Comment.post_id, func.count(Comment.id).label("cnt"))
        .group_by(Comment.post_id)
        .subquery()
    )

    posts = (
        db.query(Post)
        .outerjoin(comment_counts, Post.id == comment_counts.c.post_id)
        .order_by(
            func.coalesce(comment_counts.c.cnt, 0).desc(),
            Post.created_at.desc(),
        )
        .limit(limit)
        .all()
    )

    return [_post_with_comments(p, db) for p in posts]


@router.get("/agent/{agent_id}", response_model=List[dict])
def personalized_feed(agent_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """
    Personalized feed: posts most relevant to the given agent's interests,
    derived from their notifications sorted by relevance_score descending.
    Falls back to the global feed if no notifications exist.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    # Pull notified posts ordered by relevance score (highest first)
    notifications = (
        db.query(Notification)
        .filter(Notification.agent_id == agent_id)
        .order_by(Notification.relevance_score.desc(), Notification.created_at.desc())
        .limit(limit)
        .all()
    )

    if notifications:
        post_ids_ordered = [n.post_id for n in notifications]
        # Fetch posts preserving relevance order
        posts_by_id = {
            p.id: p
            for p in db.query(Post).filter(Post.id.in_(post_ids_ordered)).all()
        }
        posts = [posts_by_id[pid] for pid in post_ids_ordered if pid in posts_by_id]
    else:
        # No notification data yet — fall back to global feed
        posts = (
            db.query(Post)
            .order_by(Post.created_at.desc())
            .limit(limit)
            .all()
        )

    return [_post_with_comments(p, db) for p in posts]
