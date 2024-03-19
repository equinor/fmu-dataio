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
    sem: asyncio.Semaphore,
):
    params = {
        "$query": (
            f"NOT data.content: 'unset' AND "
            f"_sumo.timestamp:[{from_dt.isoformat()} TO {to_dt.isoformat()}]"
        ),
        "$size": 1_000,
        "$sort": "_doc:desc",
    }

    async with sem:
        while True:
            response = (await explorer._sumo.get_async("/search", params=params)).json()
            hits = response["hits"]["hits"]

            if not hits:
                return

            for hit in hits:
                await que.put(hit["_source"])

            params["$search_after"] = json.dumps(hits[-1]["sort"])


async def main(
    explorer: Explorer,
    start: datetime,
    step: timedelta,
    concurrency: int,
):
    tally = Counter()

    sem = asyncio.Semaphore(concurrency)
    que = asyncio.Queue[dict]()

    jobs = set[asyncio.Task]()
    now = datetime.now(tz=pytz.utc)
    stop = start + step

    while stop < now:
        job = asyncio.create_task(get(explorer, start, stop, que, sem))
        job.add_done_callback(jobs.remove)
        jobs.add(job)
        start, stop = stop, stop + step

    with tqdm(ascii=True, unit=" obj", unit_scale=True) as pbar:
        while jobs:
            try:
                obj = await asyncio.wait_for(que.get(), 0.1)
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

            if sum(tally.values()) % ((concurrency - sem._value + 1) * 1_000) == 0:
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
            "Environment to fetch data from: 'dev' for development or 'prod' "
            "for production. Defaults to 'prod'."
        ),
    )

    cliparser.add_argument(
        "--last",
        type=lambda x: timedelta(days=int(x)),
        default=timedelta(days=7),
        help="Number of days to retrospectively fetch data for. Default is 7 days.",
    )

    cliparser.add_argument(
        "--step",
        type=lambda x: timedelta(hours=int(x)),
        default=timedelta(hours=1),
        help=(
            "Temporal resolution for fetching data in hours. Determines the time "
            "span of each query. Default is 1 hours."
        ),
    )

    cliparser.add_argument(
        "--concurrency",
        type=int,
        default=16,
        help=(
            "Concurrency level for data fetching. Specifies the number of simultaneous "
            "requests. Higher values increase speed but use more resources. "
            "Default is 16."
        ),
    )

    args = cliparser.parse_args()

    if args.last <= timedelta(hours=0):
        cliparser.error("--last must be a positive number.")

    if args.concurrency <= 0:
        cliparser.error("--concurrency must be a positive number.")

    if args.step <= timedelta(hours=0):
        cliparser.error("--step must be a positive number.")

    with suppress(KeyboardInterrupt):
        asyncio.run(
            main(
                Explorer(env=args.env),
                datetime.now(tz=pytz.utc) - args.last,
                args.step,
                args.concurrency,
            )
        )
