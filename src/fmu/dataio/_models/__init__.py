from .fmu_results import FmuResults, FmuResultsSchema
from .standard_results import (
    FieldOutlineResult,
    FieldOutlineSchema,
    InplaceVolumesResult,
    InplaceVolumesSchema,
    StructureDepthFaultLinesResult,
    StructureDepthFaultLinesSchema,
)

__all__ = [
    "FmuResults",
    "FmuResultsSchema",
    "FieldOutlineResult",
    "FieldOutlineSchema",
    "InplaceVolumesResult",
    "InplaceVolumesSchema",
    "StructureDepthFaultLinesResult",
    "StructureDepthFaultLinesSchema",
]

schemas = [
    FmuResultsSchema,
    FieldOutlineSchema,
    InplaceVolumesSchema,
    StructureDepthFaultLinesSchema,
]
