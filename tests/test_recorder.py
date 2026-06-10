from afr import Recorder


def test_run_can_be_created_completed_and_listed(tmp_path):
    rec = Recorder(project="tests", db_url=f"sqlite:///{tmp_path / 'afr.db'}")

    run = rec.start_run(name="unit")
    completed = rec.complete_run(run.id)
    runs = rec.list_runs()

    assert completed.status == "completed"
    assert [item.id for item in runs] == [run.id]


def test_events_are_chronological_and_artifacts_attach(tmp_path):
    rec = Recorder(db_url=f"sqlite:///{tmp_path / 'afr.db'}")
    run = rec.start_run(name="events")

    first = rec.record_event(run.id, "note", "first")
    second = rec.record_event(run.id, "tool.call.completed", "second")
    artifact = rec.add_artifact(
        run.id, "tool_output", event_id=second.id, content_json={"ok": True}
    )

    events = rec.get_events(run.id)
    assert [event.id for event in events][-2:] == [first.id, second.id]
    assert artifact.run_id == run.id
    assert artifact.event_id == second.id
    assert artifact.sha256 is not None
