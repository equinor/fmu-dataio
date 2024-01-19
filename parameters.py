from __future__ import annotations

from typing import Dict, Union

from pydantic import RootModel


class Parameters(RootModel[Dict[str, Union[int, float, str, "Parameters"]]]):
    ...

    # root: dict[str, int | float | str | Parameters]


# class Parameters(BaseModel):
#     parameters: Union[int, float, str, "Parameters"]

# print(Parameters.model_rebuild())
# print(Parameters.model_json_schema())
print(
    Parameters.model_validate({"hello": "hello", "this": {"this": "that", "more": 1}})
)
print(
    Parameters.model_validate(
        {
            "SENSNAME": "faultseal",
            "SENSCASE": "low",
            "RMS_SEED": 1006,
            "INIT_FILES": {
                "PERM_FLUVCHAN_E1_NORM": 0.748433,
                "PERM_FLUVCHAN_E21_NORM": 0.782068,
            },
            "KVKH_CHANNEL": 0.6,
            "KVKH_US": 0.6,
            "FAULT_SEAL_SCALING": 0.1,
            "FWL_CENTRAL": 1677,
        }
    )
)
