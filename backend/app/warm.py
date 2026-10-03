"""Load the demo dataset into the store and run the whole-year analysis once, so the first Run is fast.

Run from the backend folder: .venv\Scripts\python -m app.warm
"""
from . import db, settings
from .engine import analyse, run


def main() -> None:
    settings.load_env_file()
    db.init()
    loaded = run.load_demo()
    result, cached = analyse.analysis(lambda stage, status, message: print(f"{stage:<10} {status:<8} {message}", flush=True))
    print(f"dataset {loaded['dataset_id']}: {loaded['counts']}")
    print(f"{len(result.findings):,} Findings and {len(result.matches):,} Matches ready (from cache: {cached})")


if __name__ == "__main__":
    main()
