from pathlib import Path

from app.evaluation.gold_isolation import verify_gold_isolation


def test_gold_isolation_passes_for_current_generation_sources():
    root = Path(__file__).parents[1]
    result = verify_gold_isolation(root)
    assert result["decision"] == "PASS"
    assert result["violations"] == []


def test_gold_isolation_reports_a_forbidden_marker(tmp_path):
    for relative in ("app/research/pipeline.py", "app/research/decomposer.py", "app/research/worker.py", "app/research/synthesizer.py", "app/research/planning_retrieval.py", "app/providers/ollama.py"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("safe", encoding="utf-8")
    (tmp_path / "app/research/worker.py").write_text("gold-template.csv", encoding="utf-8")
    result = verify_gold_isolation(tmp_path)
    assert result["decision"] == "FAIL"
    assert result["violations"] == [{"path": "app/research/worker.py", "marker": "gold-template.csv"}]
