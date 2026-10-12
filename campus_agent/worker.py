"""Small resumable worker for scheduled bounded iterations."""

from __future__ import annotations

import argparse
import time

from .agent import DiscoveryAgent
from .db import Database


def main() -> None:
    parser = argparse.ArgumentParser(description="Run bounded discovery iterations")
    parser.add_argument("--db", default="data/campus_agent.sqlite3")
    parser.add_argument("--university", default="University of Washington")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=0)
    args = parser.parse_args()
    db = Database(args.db)
    agent = DiscoveryAgent(db)
    previous = db.fetchone("SELECT COALESCE(MAX(iteration), 0) AS n FROM runs WHERE university=?", (args.university,))
    start = int(previous["n"]) + 1
    for iteration in range(start, start + args.iterations):
        print(agent.run_iteration(args.university, args.limit, iteration, data_mode="mock"), flush=True)
        if args.sleep_seconds:
            time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
