"""Launcher so the pipeline runs under `python -I` (isolated mode ignores cwd/PYTHONPATH).

  python -I run.py score   RAW_DIR
  python -I run.py sample  RAW_DIR
  python -I run.py export  RAW_DIR
  python -I run.py triage  <reviews.jsonl | scored.pkl> [--effort e.json] [--efficacy 0.5] [--out triage/]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "triage":
        from pipeline.triage import main  # noqa: E402
        main(sys.argv[2:])
        raise SystemExit(0)
    from pipeline.run_all import stage_export, stage_sample, stage_score  # noqa: E402
    raw = Path(sys.argv[2])
    if stage == "score":
        stage_score(raw)
    elif stage == "sample":
        stage_sample(raw)
    elif stage == "export":
        stage_export(raw)
    else:
        raise SystemExit(f"unknown stage {stage}")
