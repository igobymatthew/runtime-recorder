from afr import Recorder


def test_replay_returns_structured_dry_run_summary(tmp_path):
    rec = Recorder(db_url=f"sqlite:///{tmp_path / 'afr.db'}")
    run = rec.start_run(name="replay")
    rec.record_event(run.id, "model.call.completed", "model", output_json={"text": "answer"})
    rec.record_event(run.id, "tool.call.completed", "tool", output_json={"ok": True})
    rec.record_event(run.id, "error", "bad step", error_json={"message": "failed"}, status="error")
    rec.add_artifact(run.id, "eval_result", content_json={"passed": False})
    rec.complete_run(run.id)

    summary = rec.replay(run.id)

    assert summary["run"]["id"] == run.id
    assert len(summary["events"]) >= 5
    assert len(summary["model_calls"]) == 1
    assert len(summary["tool_calls"]) == 1
    assert len(summary["failed_steps"]) == 1
    assert summary["eval_results"][0]["content_json"]["passed"] is False
