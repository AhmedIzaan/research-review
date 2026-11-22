"""Run all six configurations, separate judging, and charts from a normal terminal."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from research_review.runner import main

if __name__ == '__main__':
    sys.exit(main())
