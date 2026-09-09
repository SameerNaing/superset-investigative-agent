"""Example: ingest a Superset chart into the canonical DB.

Usage:
    SUPERSET_BASEURL=... SUPERSET_USER_NAME=... SUPERSET_PASSWORD=... \\
    DATABASE_URL=... \\
    uv run python -m scripts.ingest_chart 74
"""

from __future__ import annotations

import argparse
import json
import sys

from app.db.session import get_session_factory
from app.services.ingestion import SupersetIngestionService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chart_id", type=int, help="Superset chart / slice ID")
    args = parser.parse_args(argv)

    session = get_session_factory()()
    try:
        service = SupersetIngestionService(session)
        result = service.ingest_chart(args.chart_id)
        query_count = len(result.analytic.queries) if result.analytic.queries else 0
        payload = {
            "analytic_id": str(result.analytic.id),
            "chart_source_id": result.chart_source_id,
            "dataset_source_id": result.dataset_source_id,
            "name": result.analytic.name,
            "query_count": query_count,
            "unsupported": result.unsupported,
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        print(f"ingestion failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
