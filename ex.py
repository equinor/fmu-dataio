import sys
from pprint import pp

from fmu.dataio.models.meta2 import Meta
from orjson import dumps
from yaml import safe_load

print(sys.argv[1])
try:
    Meta.model_validate_json(dumps(safe_load(open(sys.argv[1]))))
except Exception:
    pp(safe_load(open(sys.argv[1])))
    raise
