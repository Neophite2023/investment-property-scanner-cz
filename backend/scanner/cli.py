from __future__ import annotations

import argparse
import json

from .config import get_settings
from .pipeline import ScannerPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Investment Property Scanner CZ worker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape_parser = subparsers.add_parser("scrape")
    scrape_parser.add_argument("--transaction", choices=["sale", "rent"], default="sale")
    scrape_parser.add_argument("--no-detail", action="store_true")

    subparsers.add_parser("market-stats")
    subparsers.add_parser("rental-stats")
    subparsers.add_parser("score")
    subparsers.add_parser("report")
    subparsers.add_parser("run-all")

    args = parser.parse_args()
    pipeline = ScannerPipeline(get_settings())
    try:
        if args.command == "scrape":
            result = pipeline.scrape(args.transaction, with_detail=not args.no_detail)
            print(json.dumps({"listings": len(result)}, ensure_ascii=False, indent=2))
        elif args.command == "market-stats":
            result = pipeline.rebuild_market_statistics()
            print(json.dumps({"market_stats": len(result)}, ensure_ascii=False, indent=2))
        elif args.command == "rental-stats":
            result = pipeline.rebuild_rental_statistics()
            print(json.dumps({"rental_stats": len(result)}, ensure_ascii=False, indent=2))
        elif args.command == "score":
            result = pipeline.score_active_listings()
            print(json.dumps({"scores": len(result)}, ensure_ascii=False, indent=2))
        elif args.command == "report":
            result = pipeline.generate_daily_report()
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "run-all":
            result = pipeline.run_all()
            print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
