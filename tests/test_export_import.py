from afr import Recorder


def test_export_and_import_round_trip(tmp_path):
    source = Recorder(db_url=f"sqlite:///{tmp_path / 'source.db'}")
    run = source.start_run(name="exportable")
    event = source.record_event(run.id, "model.call.completed", "model", output_json={"text": "ok"})
    source.add_artifact(run.id, "completion", event_id=event.id, content_text="ok")
    source.complete_run(run.id)

    path = tmp_path / "trace.jsonl"
    source.export_run_jsonl(run.id, path)
    assert path.exists()
    assert path.read_text(encoding="utf-8").count("\n") >= 4

    target = Recorder(db_url=f"sqlite:///{tmp_path / 'target.db'}")
    imported_id = target.import_run_jsonl(path)

    assert imported_id == run.id
    assert target.get_run(run.id).name == "exportable"
    assert len(target.get_events(run.id)) == len(source.get_events(run.id))
