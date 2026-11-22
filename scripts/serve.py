#!/usr/bin/env python3
"""Start the local demo; never expose the project directory as a file server."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))


def main():
    parser = argparse.ArgumentParser(description='Research Review Studio — local frontend and backend')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    import uvicorn
    from research_review.web import create_app
    print(f'Open http://127.0.0.1:{args.port} in your browser.', flush=True)
    uvicorn.run(create_app(), host='127.0.0.1', port=args.port, workers=1)


if __name__ == '__main__':
    main()
