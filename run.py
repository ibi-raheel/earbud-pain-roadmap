"""Launcher so the pipeline runs under `python -I` (isolated mode ignores cwd/PYTHONPATH)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pipeline.run_all import stage_export, stage_sample, stage_score  # noqa: E402

if __name__ == "__main__":
    stage = sys.argv[1]
    if stage == "score":
        stage_score(Path(sys.argv[2]))
    elif stage == "sample":
        stage_sample()
    elif stage == "export":
        stage_export()
    else:
        raise SystemExit(f"unknown stage {stage}")
