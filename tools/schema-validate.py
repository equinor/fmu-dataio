# type: ignore
# Ex. usage: time (find schema -name "*.yml" | python3 tools/schema-example-validate.py)

import sys

from orjson import dumps
from yaml import safe_load

from fmu.dataio._models import FmuResults


def read(file):
    with open(file) as f:
        return f.read()


for file in (f.strip() for f in sys.stdin.readlines()):
    print(file)
    try:
        FmuResults.model_validate_json(dumps(safe_load(read(file))))
    except ValueError:
        from pprint import pp

        pp(safe_load(read(file)))
        raise
