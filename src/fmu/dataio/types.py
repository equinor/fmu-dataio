from __future__ import annotations

from typing import Dict, Union

from typing_extensions import Annotated, TypeAlias

Parameters: TypeAlias = Annotated[
    Dict[str, Union[str, float, int, None, "Parameters"]],
    "Nested or flat configurations for dynamically structured parameters.",
]
