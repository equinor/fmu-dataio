# type: ignore
# Ex. usage: time (find schema -name "*.yml" | python3 tools/schema-example-validate.py)

import sys

from fmu.dataio.datastructure.meta.meta import Root
from orjson import dumps
from yaml import safe_load


def read(file):
    with open(file) as f:
        return f.read()


for file in (f.strip() for f in sys.stdin.readlines()):
    print(file)
    try:
        Root.model_validate_json(dumps(safe_load(read(file))))
    except ValueError:
        from pprint import pp

        pp(safe_load(read(file)))
        raise
