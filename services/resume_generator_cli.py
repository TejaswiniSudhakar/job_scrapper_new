"""CLI wrapper for resume generation. Called by the Next.js API route."""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.resume_generator import generate_resume


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python resume_generator_cli.py <job_json_path>"}))
        sys.exit(1)

    job_path = Path(sys.argv[1])
    if not job_path.exists():
        print(json.dumps({"error": f"Job file not found: {job_path}"}))
        sys.exit(1)

    job = json.loads(job_path.read_text(encoding="utf-8"))
    result = generate_resume(job)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
