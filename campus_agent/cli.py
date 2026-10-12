from __future__ import annotations
import argparse, json, os
from pathlib import Path
from .agent import DiscoveryAgent
from .db import Database
from .evaluate import metrics
def main() -> None:
    parser = argparse.ArgumentParser(description="Scoopic campus ambassador discovery agent"); parser.add_argument("--db", default=os.getenv("DATABASE_PATH", "data/campus_agent.sqlite3")); sub = parser.add_subparsers(dest="command", required=True); sub.add_parser("init-db"); pilot = sub.add_parser("pilot"); pilot.add_argument("--university", default="University of Washington"); pilot.add_argument("--limit", type=int, default=50); pilot.add_argument("--iterations", type=int, default=2); sub.add_parser("metrics"); args = parser.parse_args(); db = Database(args.db); db.init()
    if args.command == "init-db": print(json.dumps({"database": str(Path(args.db).resolve()), "status": "initialized"}, indent=2))
    elif args.command == "metrics": print(json.dumps(metrics(db), indent=2))
    else:
        agent = DiscoveryAgent(db)
        for i in range(1, args.iterations + 1): print(json.dumps(agent.run_iteration(args.university, args.limit, i, data_mode="mock"), indent=2))
        print(json.dumps({"metrics": metrics(db), "data_mode": "mock", "note": "Fixtures only; no real leads or outreach were generated."}, indent=2))
if __name__ == "__main__": main()
