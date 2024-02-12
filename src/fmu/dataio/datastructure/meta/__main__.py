from __future__ import annotations

import json

from . import dump

if __name__ == "__main__":
    print(
        json.dumps(
            dump(),
            indent=2,
            sort_keys=True,
        )
    )
