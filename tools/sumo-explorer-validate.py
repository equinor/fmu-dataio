# type: ignore

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import suppress
from datetime import datetime, timedelta
from pprint import pformat

import pytz
from fmu.dataio.datastructure.meta import Root
from fmu.sumo.explorer import Explorer
from pydantic import ValidationError
from tqdm import tqdm


def get(env: str, days_since: int):
    explorer = Explorer(env=env)
    from_dt = datetime.now(tz=pytz.utc) - timedelta(days=days_since)
    after = None
    while True:
        response = explorer._sumo.get(
            "/search",
            {
                # Unset is not a valid content type, skip.
                "$query": (
                    f"NOT data.content:'unset' AND "
                    f"_sumo.timestamp:[{from_dt.isoformat()} TO *]"
                ),
                "$size": 1_000,
                "$sort": "_doc:asc",
                "search_after": after,
            },
        ).json()

        hits = response["hits"]["hits"]

        yield from (h["_source"] for h in hits)
        after = hits[-1]["sort"][0]


def main(env: str, days_since: int):
    tally = Counter()
    with tqdm(
        ascii=True,
        position=1,
        unit=" obj",
        unit_scale=True,
    ) as pbar:
        for m in get(env, days_since):
            pbar.update()

            try:
                parsed = Root.model_validate(m)
            except ValidationError as e:
                pbar.write(pformat(m))
                pbar.write(str(e))
                continue

            content = (
                parsed.root.data.root.content if hasattr(parsed.root, "data") else None
            )
            tally.update([(parsed.root.class_, content, parsed.root.access.asset.name)])

            if sum(tally.values()) % 2500 == 0:
                pbar.write("-" * 100)
                pbar.write(
                    "\n".join(
                        f"{tqdm.format_sizeof(v):<8} "
                        f"{fmuclass!s:<30} {fmucontent!s:<30} {name}"
                        for (fmuclass, fmucontent, name), v in sorted(
                            tally.items(), key=lambda x: x[1]
                        )
                    )
                )


if __name__ == "__main__":
    cliparser = argparse.ArgumentParser(
        description=(
            "This script fetches and processes data from FMU's Sumo "
            "over a specified number of days."
        ),
    )

    cliparser.add_argument(
        "--env",
        choices=["dev", "prod"],
        default="prod",
        help=(
            "Specify the environment to fetch data from. "
            "Choose 'dev' for development or 'prod' for production. Default is 'prod'."
        ),
    )

    cliparser.add_argument(
        "--last-n-days",
        type=int,
        default=30,
        help="Specify the number of days to look back for data. Default is 30 days.",
    )

    args = cliparser.parse_args()

    with suppress(KeyboardInterrupt):
        main(args.env, args.last_n_days)
