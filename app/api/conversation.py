from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.common import conversation_or_404, pipeline_value_error
from app.api.dependencies import get_api_runtime, get_current_user
from app.api.errors import ApiError
from app.api.knowledge import knowledge_service
from app.api.schemas import ChatRequest, ConversationCreateRequest, ConversationMessageRequest
from app.core.api_runtime import ApiRuntime
from app.research.conversation_context import build_conversation_context


router = APIRouter()


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    if not body.message.strip():
        raise ApiError(400, "MESSAGE_REQUIRED", "message is required")
    knowledge_service(runtime)
    try:
        return await runtime.run_coordinator.execute(
            body.message.strip(),
            body.condition,
            body.provider,
            owner_id=str(user.get("user_id") or user.get("id") or ""),
        )
    except ValueError as exc:
        raise pipeline_value_error(exc) from exc


@router.post("/conversations")
def create_conversation(
    body: ConversationCreateRequest | None = None,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    owner_id = str(user.get("user_id") or user.get("id") or "")
    return runtime.conversation_store.create(owner_id, body.title if body else None)


@router.get("/conversations")
def list_conversations(
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
    limit: int = Query(default=50, ge=1, le=200),
):
    owner_id = str(user.get("user_id") or user.get("id") or "")
    return {"conversations": runtime.conversation_store.list(owner_id, limit=limit)}


@router.get("/conversations/{conversation_id}")
def get_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    return conversation_or_404(conversation_id, runtime, user)


@router.post("/conversations/{conversation_id}/messages")
async def send_conversation_message(
    conversation_id: str,
    body: ConversationMessageRequest,
    user: dict[str, Any] = Depends(get_current_user),
    runtime: ApiRuntime = Depends(get_api_runtime),
):
    message = body.message.strip()
    if not message:
        raise ApiError(400, "MESSAGE_REQUIRED", "message is required")
    knowledge_service(runtime)
    conversation = conversation_or_404(conversation_id, runtime, user)
    owner_id = str(user.get("user_id") or user.get("id") or "")
    bounded_context = build_conversation_context(conversation)
    user_message = runtime.conversation_store.append_message(
        conversation_id, owner_id, role="USER", content=message
    )
    try:
        run = await runtime.run_coordinator.execute(
            message,
            body.condition,
            body.provider,
            conversation_context=bounded_context,
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
    except ValueError as exc:
        raise pipeline_value_error(exc) from exc
    run_id = str(run.get("run_id") or "")
    if run_id:
        user_message = (
            runtime.conversation_store.link_message_run(
                conversation_id,
                owner_id,
                str(user_message.get("message_id") or ""),
                run_id,
            )
            or user_message
        )
    answer = str(run.get("answer") or run.get("status") or "No answer returned.")
    assistant_message = runtime.conversation_store.append_message(
        conversation_id,
        owner_id,
        role="ASSISTANT",
        content=answer,
        run_id=run_id or None,
    )
    updated = runtime.conversation_store.get(conversation_id, owner_id)
    return {
        "conversation": updated,
        "user_message": user_message,
        "assistant_message": assistant_message,
        "run": run,
    }
