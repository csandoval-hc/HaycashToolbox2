# Auto-generated wrapper to run existing Streamlit app without modifying its code.
import os
import runpy
from pathlib import Path

from simple_auth import require_shared_password

require_shared_password()

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "apps" / "lector_edocat"

os.chdir(APP_DIR)

runpy.run_path(str(APP_DIR / "app.py"), run_name="__main__")
