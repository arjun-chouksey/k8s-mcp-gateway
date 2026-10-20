from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import StreamingResponse

from app.models import Conversation, Message
from app.security.permissions import current_actor, database, require_same_origin
from app.security.web_sessions import SessionActor


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    conversation_id: UUID | None = None


class ConversationSummary(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    role: str
    text: str
    tool_calls: list[dict] | None
    created_at: datetime


class ConversationResponse(ConversationSummary):
    messages: list[MessageResponse]


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"


def create_chat_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/conversations", response_model=list[ConversationSummary])
    async def conversations(
        db: AsyncSession = Depends(database), actor: SessionActor = Depends(current_actor),
    ) -> list[ConversationSummary]:
        rows = (await db.scalars(
            select(Conversation).where(Conversation.user_id == actor.id)
            .order_by(Conversation.updated_at.desc(), Conversation.id.desc()).limit(100)
        )).all()
        return [ConversationSummary.model_validate(row, from_attributes=True) for row in rows]

    @router.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
    async def conversation(
        conversation_id: UUID, db: AsyncSession = Depends(database),
        actor: SessionActor = Depends(current_actor),
    ) -> ConversationResponse:
        row = await db.get(Conversation, conversation_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        if row.user_id != actor.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Conversation access denied")
        messages = (await db.scalars(
            select(Message).where(Message.conversation_id == row.id)
            .order_by(Message.created_at.asc(), Message.id.asc())
        )).all()
        return ConversationResponse(
            id=row.id, title=row.title, created_at=row.created_at, updated_at=row.updated_at,
            messages=[MessageResponse(
                id=item.id, role=item.role, text=item.text,
                tool_calls=item.tool_calls_json, created_at=item.created_at,
            ) for item in messages],
        )

    @router.post("/api/chat")
    async def chat(
        payload: ChatRequest, request: Request, db: AsyncSession = Depends(database),
        actor: SessionActor = Depends(current_actor),
    ) -> StreamingResponse:
        require_same_origin(request)
        from app.chat.agent import redact_text
        clean_prompt = redact_text(payload.prompt.strip())
        if payload.conversation_id:
            conversation = await db.get(Conversation, payload.conversation_id)
            if conversation is None:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
            if conversation.user_id != actor.id:
                raise HTTPException(status.HTTP_403_FORBIDDEN, "Conversation access denied")
        else:
            conversation = Conversation(user_id=actor.id, title=clean_prompt[:120])
            db.add(conversation)
            await db.flush()
        db.add(Message(conversation_id=conversation.id, role="user", text=clean_prompt, tool_calls_json=None))
        await db.commit()
        conversation_id = conversation.id

        async def events() -> AsyncIterator[str]:
            async for event in request.app.state.chat_agent.run(actor, conversation_id, clean_prompt):
                yield _sse(event)

        return StreamingResponse(events(), media_type="text/event-stream", headers={
            "Cache-Control": "no-store", "X-Accel-Buffering": "no",
        })
    return router
