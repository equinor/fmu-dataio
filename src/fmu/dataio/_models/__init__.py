from .fmu_results import FmuResults, FmuResultsSchema
from .products import InplaceVolumesResult, InplaceVolumesSchema

__all__ = [
    "FmuResults",
    "FmuResultsSchema",
    "InplaceVolumesResult",
    "InplaceVolumesSchema",
]

schemas = [FmuResultsSchema, InplaceVolumesSchema]
