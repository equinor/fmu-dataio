# type: ignore

from __future__ import annotations

from collections import Counter
from contextlib import suppress
from pprint import pp
from random import sample

from fmu.dataio.datastructure.meta import Root
from fmu.sumo.explorer import Explorer
from tqdm import tqdm


def lazy_sampler(x, lenx, k=100):
    if lenx <= 0:
        return

    sampled_idx = sample(range(lenx), k=k) if k < lenx else range(lenx)

    for i in sampled_idx:
        with suppress(IndexError):
            yield x[i]


def gen():
    e = Explorer(env="dev")
    for c in sample(tuple(e.cases), 25):
        yield c.metadata

        for cube in lazy_sampler(c.cubes, len(c.cubes)):
            yield cube.metadata

        for surf in lazy_sampler(c.surfaces, len(c.surfaces)):
            yield surf.metadata

        for poly in lazy_sampler(c.polygons, len(c.surfaces)):
            yield poly.metadata

        for tab in lazy_sampler(c.tables, len(c.tables)):
            yield tab.metadata

        for dic in lazy_sampler(c.dictionaries, len(c.dictionaries)):
            yield dic.metadata


if __name__ == "__main__":
    tally = Counter()
    with tqdm(ascii=True, position=1) as pbar:
        for m in gen():
            pbar.update()
            try:
                parsed = Root.model_validate(m)
                content = (
                    parsed.root.data.root.content
                    if hasattr(parsed.root, "data")
                    else None
                )
                tally.update([(parsed.root.class_, content)])
                if sum(tally.values()) % 25 == 0:
                    pbar.write("-" * 100)
                    pbar.write("\n".join(str(v) for v in tally.items()))
            except Exception as e:
                print(str(e))
                pp(m)
                raise
