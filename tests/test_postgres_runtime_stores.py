from __future__ import annotations

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker

from app.storage.postgres.base import Base
from app.storage.postgres.models import SessionRecord
from app.storage.postgres.runtime import (
    PostgresAuthStore,
    PostgresConversationStore,
    PostgresRunStore,
    PostgresSourceStore,
)


def _factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'runtime.sqlite3'}")
    event.listen(engine, "connect", lambda connection, _record: connection.create_function("btrim", 1, lambda value: value.strip()))
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_postgres_auth_store_persists_users_and_revocable_sessions(tmp_path, monkeypatch):
    store = PostgresAuthStore(_factory(tmp_path))
    user = store.register(email="person@example.test", password="long-enough-password")
    authenticated, token, session = store.authenticate(
        identifier="PERSON@example.test", password="long-enough-password"
    )

    assert authenticated["user_id"] == user["user_id"]
    assert store.resolve(token)["user_id"] == user["user_id"]
    assert store.session_for_token(token)["session_id"] == session["session_id"]
    assert store.revoke(token) is True
    assert store.session_for_token(token) is None


def test_postgres_source_and_run_stores_are_owner_scoped(tmp_path):
    factory = _factory(tmp_path)
    auth = PostgresAuthStore(factory)
    owner_a = auth.register(email="a@example.test", password="long-enough-password")
    owner_b = auth.register(email="b@example.test", password="long-enough-password")
    source_a = PostgresSourceStore(factory, owner_a["user_id"])
    source_b = PostgresSourceStore(factory, owner_b["user_id"])

    imported_a = source_a.import_text("shared.md", "Private source body")
    imported_b = source_b.import_text("shared.md", "Private source body")
    assert imported_a["source_id"] != imported_b["source_id"]
    assert source_a.source(imported_a["source_id"])
    assert source_b.source(imported_a["source_id"]) is None
    assert source_b.list_sources() == [{
        "source_id": imported_b["source_id"],
        "source_name": "shared.md",
        "chunk_count": 1,
    }]

    run = {"run_id": "run_owner_a", "status": "COMPLETE", "query": "Private", "answer": "Grounded"}
    runs_a = PostgresRunStore(factory, owner_a["user_id"])
    runs_b = PostgresRunStore(factory, owner_b["user_id"])
    runs_a.save(run)
    assert runs_a.get("run_owner_a") == run
    assert runs_b.get("run_owner_a") is None
    assert runs_b.list() == []


def test_postgres_conversation_messages_persist_with_owner_and_order(tmp_path):
    factory = _factory(tmp_path)
    auth = PostgresAuthStore(factory)
    owner = auth.register(email="chat@example.test", password="long-enough-password")
    conversations = PostgresConversationStore(factory, owner["user_id"])
    created = conversations.create("First chat")
    conversations.add_message(created["conversation_id"], "USER", "Question")
    conversations.add_message(created["conversation_id"], "ASSISTANT", "Answer")

    restored = conversations.get(created["conversation_id"])
    assert [message["content"] for message in restored["messages"]] == ["Question", "Answer"]
    assert [message["sequence_number"] for message in restored["messages"]] == [0, 1]
    assert PostgresConversationStore(factory, "other-owner").get(created["conversation_id"]) is None
    assert "sessions" in inspect(factory.kw["bind"]).get_table_names()
    assert SessionRecord.__tablename__ == "sessions"
