"""Run this yourself, with a real Gemini API key in .env, to see what the
AI mission parser actually produces for a real objective — this is the
"spot-checked by you" step the build plan calls for. The automated test
suite (tests/services/test_mission.py) can't do this part: it runs
without any network access to Google's API, using canned responses to
prove the code plumbing works, not that Gemini's actual answers are good.

Usage:
    python scripts/try_mission_parser.py "Find Series A SaaS companies that just raised funding"
"""

import asyncio
import json
import sys

from app.services.mission import parse_objective_to_icp


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/try_mission_parser.py "your objective here"')
        raise SystemExit(1)

    raw_objective = sys.argv[1]
    icp = await parse_objective_to_icp(raw_objective)
    print(json.dumps(icp.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
