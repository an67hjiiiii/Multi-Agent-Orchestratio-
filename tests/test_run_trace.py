from app.run.trace import append_run_event, persisted_run_events


def test_trace_helpers_preserve_event_shape_and_legacy_read_fallback():
    events: list[dict] = []

    append_run_event(events, "task_completed", task_id="T1", result={"status": "COMPLETE"})

    assert events[0]["stage"] == "task_completed"
    assert events[0]["task_id"] == "T1"
    assert events[0]["result"] == {"status": "COMPLETE"}
    assert events[0]["ts"].endswith("+00:00")
    assert persisted_run_events({"trace": [events[0], "ignored"]}) == events


def test_trace_helpers_prefer_events_and_return_copies():
    run = {"events": [{"stage": "run_started"}], "trace": [{"stage": "legacy"}]}

    observed = persisted_run_events(run)

    assert observed == [{"stage": "run_started"}]
    assert observed[0] is not run["events"][0]
