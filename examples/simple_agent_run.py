from afr import Recorder
from afr.evals import exact_match

rec = Recorder(project="demo", db_url="sqlite:///afr.db")
run = rec.start_run(name="sample")

with rec.event(run.id, "model.call.started", name="call example model"):
    rec.add_artifact(run.id, "prompt", content_text="Say hello")

rec.record_event(
    run.id,
    event_type="tool.call.completed",
    name="search files",
    input_json={"query": "hello"},
    output_json={"matches": ["hello.txt"]},
)

rec.add_artifact(run.id, "eval_result", content_json=exact_match("hello", "hello"))
rec.complete_run(run.id)
print(run.id)
