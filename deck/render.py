"""Render index.html to deck.pdf and per-slide PNGs with headless Chrome."""
import subprocess, sys
from pathlib import Path
from PIL import Image

HERE = Path(__file__).parent
CHROME = r"C:/Program Files/Google/Chrome/Application/chrome.exe"
URL = (HERE / "index.html").resolve().as_uri()
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
N = 7

common = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
          "--virtual-time-budget=8000", "--force-device-scale-factor=1"]
subprocess.run(common + [f"--print-to-pdf={OUT / 'LedgerLens_Fintechstico.pdf'}", "--no-pdf-header-footer", URL], check=True)
if "--pdf-only" not in sys.argv:
    full = OUT / "full.png"
    subprocess.run(common + [f"--screenshot={full}", f"--window-size=1920,{1080 * N}", URL], check=True)
    im = Image.open(full)
    for i in range(N):
        im.crop((0, i * 1080, 1920, (i + 1) * 1080)).save(OUT / f"slide{i + 1}.png")
print("rendered")
