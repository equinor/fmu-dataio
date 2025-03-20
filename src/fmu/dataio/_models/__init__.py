from .fmu_results import FmuResults, FmuResultsSchema
from .standard_results import (
    InplaceVolumesResult,
    InplaceVolumesSchema,
    StructureDepthFaultLinesResult,
    StructureDepthFaultLinesSchema,
)

__all__ = [
    "FmuResults",
    "FmuResultsSchema",
    "InplaceVolumesResult",
    "InplaceVolumesSchema",
    "StructureDepthFaultLinesResult",
    "StructureDepthFaultLinesSchema",
]

schemas = [
    FmuResultsSchema,
    InplaceVolumesSchema,
    StructureDepthFaultLinesSchema,
]
