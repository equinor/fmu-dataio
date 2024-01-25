# Tool for building the datastructure.rst file.
# Ex. usage: python3 docs/gen-datastructure.py > docs/datastructure.rst

from __future__ import annotations

import inspect

from fmu.dataio.datastructure.meta import content, meta, specification
from pydantic import BaseModel, RootModel


def pydantic_members(m):
    for name, obj in inspect.getmembers(m):
        if (
            inspect.isclass(obj)
            and issubclass(obj, (RootModel, BaseModel))
            and obj.__module__.startswith("fmu.dataio.datastructure")
        ):
            yield obj.__module__, name


if __name__ == "__main__":
    print(
        """.. Do not modifly this file manuely, see: docs/gen-datastructure.py
Meta export datastructures
==========================\n\n"""
    )

    settings = "\n".join(("  :model-show-json: false",))
    for module in (meta, content, specification):
        for module_path, name in pydantic_members(module):
            print(f".. autopydantic_model:: {module_path}.{name}\n{settings}\n")
