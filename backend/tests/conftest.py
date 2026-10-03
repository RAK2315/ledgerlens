import os
import sys
import time
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
MINI = BACKEND.parent / "ml" / "tests" / "fixtures" / "mini.xlsx"


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    """The API over the small fixture workbook, with its own database, cache and generated GSTR-2B lines."""
    from ledgerlens_ml import load_dataset
    from ledgerlens_ml.augment import build_augmentation, write_augmentation

    root = tmp_path_factory.mktemp("backend")
    derived = root / "derived"
    write_augmentation(build_augmentation(load_dataset(MINI, derived_dir=root / "none", expected_sha256=None)), derived)
    os.environ.update({
        "LEDGERLENS_DATASET": str(MINI), "LEDGERLENS_DERIVED": str(derived), "LEDGERLENS_DB": str(root / "test.db"),
        "LEDGERLENS_CACHE": str(root / "cache"), "LEDGERLENS_STAGE_DELAY": "0", "LLM_MODE": "template_only",
    })
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def loaded(client):
    return client.post("/api/demo/load").json()


@pytest.fixture(scope="session")
def run_id(client, loaded):
    run = client.post("/api/runs", json={"dataset_id": loaded["dataset_id"], "period": "2025-09"}).json()["run_id"]
    for _ in range(600):
        if client.get(f"/api/runs/{run}").json()["status"] in ("done", "failed"):
            break
        time.sleep(0.1)
    return run
