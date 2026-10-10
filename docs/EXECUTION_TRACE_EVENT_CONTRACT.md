# Execution trace event contract

This document defines the task-level lifecycle events recorded while prepared
research tasks execute. Run-level trace identity, terminal statuses, and
retrieval events remain governed by the existing run contracts.

## Envelope and correlation

Each event is an append-only mapping with a `stage` name and a UTC ISO-8601
`ts` timestamp. Event-specific fields are additive. Consumers should preserve
unknown fields and use the recorded order when rendering a trace.

Task events correlate through `task_id`. A task that begins execution records
one `task_started` event, followed by either `task_completed` or
`task_failed`. Tasks not reached because execution stops at a run budget have
no task event.

| Stage | Required fields | Meaning |
| --- | --- | --- |
| `task_started` | `task_id`, `depends_on` | Emitted before resolving the task's evidence and calling its worker. `depends_on` contains the declared task IDs; dependency answers are not copied into the event. |
| `task_completed` | `result` | Emitted after a `WorkerResult` is produced. The existing result mapping carries the correlating `task_id`, task status, answer, and evidence/citation fields. The stage means a result was returned; its nested status remains authoritative and is not inferred from the event name. |
| `task_failed` | `task_id`, `error_type` | Emitted when dependency-context preparation, evidence resolution, or worker execution raises. It identifies the task and exception class without copying exception text into this task event. The exception continues to the coordinator, which records `run_failed` and persists the run as `FAILED`. |

`run_budget_exceeded` follows the completed task whose usage crossed the cap.
It does not mean that task failed. The coordinator remains responsible for the
run-level `run_finished` or `run_failed` event and terminal run status.

## Sample event data

The rows below are illustrative. Timestamps and IDs are examples, not runtime
or experiment evidence.

Successful dependent task:

```json
[
  {
    "stage": "task_started",
    "ts": "2026-10-10T09:30:00+00:00",
    "task_id": "T2",
    "depends_on": ["T1"]
  },
  {
    "stage": "task_completed",
    "ts": "2026-10-10T09:30:02+00:00",
    "result": {
      "task_id": "T2",
      "domain": "api_architecture",
      "status": "COMPLETE",
      "answer": "The endpoint validates the request before processing it.",
      "evidence_ids": ["chunk-1"],
      "citations": ["chunk-1"],
      "invalid_citations": [],
      "missing_information": [],
      "status_reason": ""
    }
  }
]
```

Failed task followed by the coordinator's terminal run event:

```json
[
  {
    "stage": "task_started",
    "ts": "2026-10-10T09:31:00+00:00",
    "task_id": "T3",
    "depends_on": []
  },
  {
    "stage": "task_failed",
    "ts": "2026-10-10T09:31:05+00:00",
    "task_id": "T3",
    "error_type": "TimeoutError"
  },
  {
    "stage": "run_failed",
    "ts": "2026-10-10T09:31:05+00:00",
    "error_type": "TimeoutError",
    "error": "provider timed out"
  }
]
```
