"""Launcher so the pipeline runs under `python -I` (isolated mode ignores cwd/PYTHONPATH)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.run_all import stage_export, stage_sample, stage_score  # noqa: E402

if __name__ == "__main__":
    stage = sys.argv[1]
    raw = Path(sys.argv[2])
    if stage == "score":
        stage_score(raw)
    elif stage == "sample":
        stage_sample(raw)
    elif stage == "export":
        stage_export(raw)
    else:
        raise SystemExit(f"unknown stage {stage}")
