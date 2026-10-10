from app.evaluation.trace_metric_audit import compare_trace_and_metrics


def test_comparison_accepts_consistent_successful_attempt():
    attempt = {
        "status": "COMPLETE",
        "events": [
            {
                "stage": "task_retrieval",
                "candidates": ["c1", "c2"],
                "selected": ["c1"],
                "dropped": [{"chunk_id": "c2", "reason": "budget"}],
            },
            {"stage": "run_finished", "status": "COMPLETE"},
        ],
        "metrics": {
            "input_tokens": 7,
            "output_tokens": 3,
            "total_tokens": 10,
            "retrieved_chunks": 2,
            "selected_chunks": 1,
            "dropped_chunks": 1,
        },
    }

    assert compare_trace_and_metrics(attempt) == {
        "terminal_status_matches_trace": True,
        "token_totals_match": True,
        "task_retrieval_counts_match": True,
    }


def test_comparison_accepts_consistent_failed_attempt_with_unavailable_retrieval_counts():
    attempt = {
        "status": "FAILED",
        "events": [
            {"stage": "retrieval_failed", "error_type": "RuntimeError"},
            {"stage": "run_failed", "error_type": "RuntimeError"},
        ],
        "metrics": {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "retrieved_chunks": 0,
            "selected_chunks": 0,
            "dropped_chunks": 0,
        },
    }

    assert compare_trace_and_metrics(attempt) == {
        "terminal_status_matches_trace": True,
        "token_totals_match": True,
        "task_retrieval_counts_match": None,
    }


def test_comparison_flags_persisted_status_token_and_retrieval_mismatches():
    attempt = {
        "status": "PARTIAL",
        "events": [
            {
                "stage": "task_retrieval",
                "candidates": ["c1"],
                "selected": ["c1"],
                "dropped": [],
            },
            {"stage": "run_finished", "status": "COMPLETE"},
        ],
        "metrics": {
            "input_tokens": 7,
            "output_tokens": 3,
            "total_tokens": 11,
            "retrieved_chunks": 2,
            "selected_chunks": 1,
            "dropped_chunks": 0,
        },
    }

    assert compare_trace_and_metrics(attempt) == {
        "terminal_status_matches_trace": False,
        "token_totals_match": False,
        "task_retrieval_counts_match": False,
    }


def test_comparison_marks_absent_trace_or_metrics_as_unavailable():
    assert compare_trace_and_metrics({"status": "COMPLETE", "events": [], "metrics": {}}) == {
        "terminal_status_matches_trace": None,
        "token_totals_match": None,
        "task_retrieval_counts_match": None,
    }
