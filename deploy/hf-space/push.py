"""Push the backend to the Hugging Face Space. Only files tracked by git are sent, so backend/.env never leaves the machine.

Usage, from the repo root, logged in with hf auth login: python deploy/hf-space/push.py [owner/space-name]
"""
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

REPO = Path(__file__).resolve().parents[2]
SPACE = sys.argv[1] if len(sys.argv) > 1 else "rak2315/ledgerlens-api"

with tempfile.TemporaryDirectory() as folder:
    stage = Path(folder)
    archive = subprocess.run(["git", "archive", "HEAD", "ml", "backend", "data"], cwd=REPO, check=True, capture_output=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(stage)
    shutil.rmtree(stage / "backend" / "tests", ignore_errors=True)
    shutil.rmtree(stage / "ml" / "tests", ignore_errors=True)
    for name in ("Dockerfile", "README.md"):
        shutil.copy(Path(__file__).with_name(name), stage / name)
    api = HfApi()
    # Creating a Docker Space needs a paid plan on some accounts; an existing Space is reused as it is.
    if not api.repo_exists(SPACE, repo_type="space"):
        api.create_repo(SPACE, repo_type="space", space_sdk="docker")
    api.upload_folder(repo_id=SPACE, repo_type="space", folder_path=stage, commit_message="Deploy the LedgerLens backend", delete_patterns=["*"])
    print("pushed to", f"https://huggingface.co/spaces/{SPACE}")
