import sys
from pathlib import Path

# Make the project root importable for all tests without duplicating path hacks.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
for entry in (PROJECT_ROOT, SRC_DIR):
    path_str = str(entry)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
