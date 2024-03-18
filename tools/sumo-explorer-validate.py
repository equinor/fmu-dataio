# type: ignore

from __future__ import annotations

from collections import Counter
from contextlib import suppress
from pprint import pformat

from fmu.dataio.datastructure.meta import Root
from fmu.sumo.explorer import Explorer
from more_itertools import roundrobin
from pydantic import ValidationError
from tqdm import tqdm


def safe_generator(gen):
    try:
        yield from gen
    except IndexError:
        return


def case_meta_roundrobin():
    for case in Explorer().cases:
        yield case.metadata
        yield from roundrobin(
            safe_generator(c.metadata for c in case.cubes),
            safe_generator(c.metadata for c in case.dictionaries),
            safe_generator(c.metadata for c in case.polygons),
            safe_generator(c.metadata for c in case.surfaces),
            safe_generator(c.metadata for c in case.tables),
        )


def main():
    tally = Counter()
    with tqdm(
        ascii=True,
        position=1,
        unit=" obj",
        unit_scale=True,
    ) as pbar:
        for m in case_meta_roundrobin():
            pbar.update()
            try:
                parsed = Root.model_validate(m)
                content = (
                    parsed.root.data.root.content
                    if hasattr(parsed.root, "data")
                    else None
                )
                tally.update(
                    [(parsed.root.class_, content, parsed.root.access.asset.name)]
                )
                if sum(tally.values()) % 100 == 0:
                    pbar.write("-" * 100)
                    pbar.write(
                        "\n".join(
                            f"{v:<6} {fmuclass!s:<30} {fmucontent!s:<30} {name}"
                            for (fmuclass, fmucontent, name), v in sorted(
                                tally.items(), key=lambda x: x[1]
                            )
                        )
                    )
            except ValidationError as e:
                pbar.write(pformat(m))
                pbar.write(str(e))


if __name__ == "__main__":
    with suppress(KeyboardInterrupt):
        main()
