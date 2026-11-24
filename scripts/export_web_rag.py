"""Compatibility entry point for the unified-book website builder."""

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_zohar_tudastar import build


if __name__ == "__main__":
    build()
