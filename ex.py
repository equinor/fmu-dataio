import sys

from fmu.dataio.models.meta.model import Root
from orjson import dumps
from yaml import safe_load


def read(file):
    with open(file) as f:
        return f.read()


for file in (f.strip() for f in sys.stdin.readlines()):
    print(file)
    Root.model_validate_json(dumps(safe_load(read(file))))
