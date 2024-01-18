from __future__ import annotations

from contextlib import suppress
from random import sample

from fmu.sumo.explorer import Explorer
from tqdm import tqdm

from src.fmu.dataio.models.meta2 import Meta


def lazy_sampler(x, lenx, k=100):
    if lenx <= 0:
        return

    sampled_idx = sample(range(lenx), k=k) if k < lenx else range(lenx)

    for i in sampled_idx:
        with suppress(IndexError):
            yield x[i]


def gen():
    e = Explorer(env="dev")
    for c in tqdm(sample(tuple(e.cases), 3), ascii=True, position=0):
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
    root_classes = set()
    for m in tqdm(gen(), ascii=True, position=1):
        try:
            root_classes.add(Meta.model_validate(m).class_)
        except Exception:
            from pprint import pp
            pp(m)
            raise

    print("-->>> All good in da hood.")
    print(root_classes)
