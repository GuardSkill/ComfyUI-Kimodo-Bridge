"""Install the embedded Kimodo package and optional Rive renderer runtime."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

subprocess.check_call([sys.executable, "-m", "pip", "install", "-e", str(ROOT / "kimodo")])

npm = shutil.which("npm")
if npm:
    subprocess.check_call([npm, "ci", "--omit=dev", "--ignore-scripts"], cwd=ROOT)
else:
    print("[Kimodo Motion Bridge] npm not found: core/Unity nodes work, "
          "but Rive MP4 rendering requires Node.js 18+ and `npm install`.")
