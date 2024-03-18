# type: ignore
from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from contextlib import suppress
from datetime import datetime, timedelta
from pprint import pformat

import pytz
from fmu.dataio.datastructure import meta
from fmu.sumo.explorer import Explorer
from pydantic import ValidationError
from tqdm import tqdm


async def get(
    explorer: Explorer,
    from_dt: datetime,
    to_dt: datetime,
    que: asyncio.Queue[dict],
):
    params = {
        "$query": (
            f"NOT data.content: 'unset' AND "
            f"_sumo.timestamp:[{from_dt.isoformat()} TO {to_dt.isoformat()}]"
        ),
        "$size": 1_000,
        "$sort": "_doc:desc",
    }

    while True:
        response = (await explorer._sumo.get_async("/search", params=params)).json()
        hits = response["hits"]["hits"]

        for hit in hits:
            await que.put(hit["_source"])

        try:
            params["$search_after"] = json.dumps(hits[-1]["sort"])
        except IndexError:
            return


async def main(env: str, last_n_days: int, concurrency: int):
    tally = Counter()

    jobs = set[asyncio.Task]()
    que = asyncio.Queue[dict]()

    step = timedelta(days=last_n_days) / concurrency
    start = datetime.now(tz=pytz.utc) - timedelta(days=last_n_days)
    stop = start + step
    explorer = Explorer(env=env)

    for _ in range(concurrency):
        job = asyncio.create_task(get(explorer, start, stop, que))
        job.add_done_callback(jobs.remove)
        jobs.add(job)

        start, stop = start + step, stop + step

    with tqdm(ascii=True, unit=" obj", unit_scale=True) as pbar:
        while jobs:
            try:
                obj = await asyncio.wait_for(que.get(), 1)
            except asyncio.TimeoutError:
                continue

            pbar.update()

            try:
                parsed = meta.Root.model_validate(obj)
            except ValidationError as e:
                pbar.write(pformat(obj))
                pbar.write(str(e))
                continue

            tally.update(
                [
                    (
                        parsed.root.class_,
                        parsed.root.data.root.content
                        if hasattr(parsed.root, "data")
                        else None,
                        parsed.root.access.asset.name,
                    )
                ]
            )

            if sum(tally.values()) % ((len(jobs) + 1) * 1_000) == 0:
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
            "This script fetches and processes data from Sumo "
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

    cliparser.add_argument(
        "--concurrency",
        type=int,
        default=16,
        help=(
            "Specify the level of concurrency for the data fetching process. "
            "This defines how many threads will be used to parallelize the data "
            "retrieval, allowing for faster processing by dividing the query into "
            "smaller time-buckets. Higher values can significantly reduce processing "
            "time at the cost of increased resource usage. Default is 16."
        ),
    )

    args = cliparser.parse_args()

    if args.last_n_days <= 0:
        cliparser.error("--last-n-days must be a positive number.")

    if args.concurrency <= 0:
        cliparser.error("--concurrency must be a positive number.")

    with suppress(KeyboardInterrupt):
        asyncio.run(main(args.env, args.last_n_days, args.concurrency))
