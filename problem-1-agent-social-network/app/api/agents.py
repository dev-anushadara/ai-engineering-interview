import json
import secrets
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Agent, Notification
from app.notification_service import NotificationService
from app.schemas import AgentCreate, AgentOut, NotificationOut

router = APIRouter(prefix="/agents", tags=["agents"])

notification_service = NotificationService()


@router.post("/register", response_model=dict, status_code=201)
def register_agent(agent_data: AgentCreate, db: Session = Depends(get_db)):
    """Register a new AI agent. Returns AgentOut + api_key (shown only once)."""
    api_key = secrets.token_hex(32)
    agent = Agent(
        id=str(uuid.uuid4()),
        name=agent_data.name,
        company=agent_data.company,
        description=agent_data.description,
        interests=json.dumps(agent_data.interests),
        api_key=api_key,
        is_active=True,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    agent_out = AgentOut.model_validate(agent)
    return {
        **agent_out.model_dump(),
        "api_key": api_key,
        "note": "Save this api_key — it will not be shown again.",
    }


@router.get("/", response_model=List[AgentOut])
def list_agents(db: Session = Depends(get_db)):
    """List all active agents."""
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    return [AgentOut.model_validate(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get a specific agent by ID."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    return AgentOut.model_validate(agent)


@router.get("/{agent_id}/notifications", response_model=List[NotificationOut])
def get_notifications(agent_id: str, db: Session = Depends(get_db)):
    """Get unread notifications for an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")
    notifications = notification_service.get_pending_notifications(db, agent_id)
    return [NotificationOut.model_validate(n) for n in notifications]


@router.post("/{agent_id}/notifications/{notification_id}/read", status_code=200)
def mark_notification_read(
    agent_id: str,
    notification_id: str,
    db: Session = Depends(get_db),
):
    """Mark a notification as read."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found.")

    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.agent_id == agent_id,
        )
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=404,
            detail=f"Notification '{notification_id}' not found for this agent.",
        )

    notification_service.mark_read(db, notification_id)
    return {"message": "Notification marked as read.", "notification_id": notification_id}
