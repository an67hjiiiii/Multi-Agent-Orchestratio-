from __future__ import annotations

from fastapi import APIRouter

from app.api import admin, auth, conversation, evidence, knowledge, retrieval, run, settings, tasks, trace
from app.api.common import (
    assert_plite_profile,
    conversation_or_404,
    get_p_lite_pipeline,
    planning_value_error,
    pipeline_value_error,
    run_evidence_ids,
    run_or_404,
    runtime_config,
    validate_decomposition_result,
)
from app.api.knowledge import (
    as_record,
    call_knowledge_import,
    call_knowledge_method,
    chunk_record,
    knowledge_method,
    knowledge_service,
    knowledge_status,
    lexical_status,
    vector_backend_requested,
)
from app.api.tasks import OllamaProvider


router = APIRouter(prefix="/api")
for child_router in (
    settings.router,
    auth.router,
    admin.router,
    knowledge.router,
    retrieval.router,
    run.router,
    trace.router,
    evidence.router,
    conversation.router,
    tasks.router,
):
    router.include_router(child_router)


# Keep previous helper names importable for local clients and focused tests.
_auth_error = auth.auth_error
_auth_payload = auth.auth_payload
_set_session_cookie = auth.set_session_cookie
_clear_session_cookie = auth.clear_session_cookie
_login_identifier = auth.login_identifier
_runtime_config = runtime_config
_pipeline_value_error = pipeline_value_error
_assert_plite_profile = assert_plite_profile
_validate_decomposition_result = validate_decomposition_result
_planning_value_error = planning_value_error
_vector_backend_requested = vector_backend_requested
_knowledge_service = knowledge_service
_knowledge_method = knowledge_method
_lexical_status = lexical_status
_call_knowledge_method = call_knowledge_method
_as_record = as_record
_chunk_record = chunk_record
_call_knowledge_import = call_knowledge_import
_knowledge_status = knowledge_status
_run_or_404 = run_or_404
_conversation_or_404 = conversation_or_404
_run_evidence_ids = run_evidence_ids
