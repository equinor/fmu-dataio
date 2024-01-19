import sys
from pprint import pp

from fmu.dataio.models.meta2 import Meta
from orjson import dumps
from pydantic import ValidationError
from yaml import safe_load


def read(file):
    with open(file) as f:
        return f.read()

for file in (f.strip() for f in sys.stdin.readlines()):
    print(file)
    try:
        Meta.model_validate_json(dumps(safe_load(read(file))))
    except ValidationError as e:
        print(str(e))
        pp(safe_load(read(file)))
    print("-" * 100)
