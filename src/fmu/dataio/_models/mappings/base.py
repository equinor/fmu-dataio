from enum import Enum
from pathlib import Path
from typing import List, Literal
from uuid import UUID

from pydantic import BaseModel, RootModel

from fmu.dataio._models.enums import Content

"""
Requirements:
- Can work with existing data + data formats, at least for set-up
- We want to persist these data somewhere (.fmu most likely, in our own form (mapping))
- Mappings can be located and used by other elements in the metadata (accessing official
  names for exported objects)
- Sumo may need data present in every object to index efficiently


Types:
    Wells (case)
    Stratigraphy (case) -> unofficial -> official

    Collections (realization) (do we have a use case for this?)
    Parent-Child (realization) -> relationship mapping (hierarchical)
    Stratigraphy (instance-of relationship)
    FIPNUM-Regions-Zones (realization)
    Regions-Regions (realization)

Stratigraphic mapping:
    TopVolantis:
      stratigraphic: True
      name: VOLANTIS GP. Top  # this is the official DB name
      # additional names, given for demo purpose:
      alias:
        - TopVOLANTIS
        - TOP_VOLANTIS

Well mapping:
    NO 25/2-25 - SMDA Unique Well Identifier
    NO 25/2-25 A - SMDA Name (wellbore identifier)
    25_2-25A - RMS Name
    25A - Eclipse

Parent-Child mapping:
    geogrid--perm.roff
    geogrid.roff
"""


# class MappingType(str, Enum):
#     """
#     Types:
#         Wells (case)
#         Stratigraphy (case) -> unofficial -> official

#         Collections (realization) (do we have a use case for this?)
#         Parent-Child (realization) -> relationship mapping (hierarchical)
#         Stratigraphy (instance-of relationship)
#         FIPNUM-Regions-Zones (realization)
#         Regions-Regions (realization)
#     """

#     case = "case"
#     realization = "realization"


class MappingType(str, Enum):
    """The discriminator used between mappings.

    Each of these types should have their own mapping class derived of some sort of
    mapping.
    """

    fault = "fault"
    stratigraphy = "stratigraphy"
    well = "well"


class RelationType(str, Enum):
    """The kind of relation this mapping represents."""

    alias = "alias"
    child_to_parent = "child_to_parent"
    equivalent = "equivalent"
    fmu_to_target = "fmu_to_target"
    predecessor_to_successor = "predecessor_to_successor"


class Source(BaseModel):
    name: str  # RMS, Eclipse, ...
    origination: Literal["user", "automatic"]


class BaseMapping(BaseModel):
    """The base mapping containing the fields all mappings should contain.

    These fields will be contained in every individual mapping entry."""

    source_system: str
    target_system: Literal["smda"]
    mapping_type: MappingType
    # confidence: float


# ------------------- Standard mappings


class IdentifierMapping(BaseMapping):
    """Base class for a one-to-one or many-to-one mapping of identifiers.

    This mapping represents takes some identifier from one source and correlates it to
    an identifier in a target. Most often this target will be some official masterdata
    store like SMDA."""

    source_id: str
    target_id: str  # NO 22/25A
    target_uuid: UUID


# User story: StratigraphyMapping / WellMapping
# As a data consumer, I would like to know which masterdata an FMU name maps to, if one
# exists.


class StratigraphyMapping(IdentifierMapping):
    """Represents a mapping from stratigraphic aliases identifiers to an official
    identifier."""

    mapping_type: Literal[MappingType.stratigraphy] = MappingType.stratigraphy
    # specific stratigraphy mapping fields ...


# Stratigraphic mapping:
#     TopVolantis:
#       stratigraphic: True
#       name: VOLANTIS GP. Top  # this is the official DB name
#       # additional names, given for demo purpose:
#       alias:
#         - TopVOLANTIS
#         - TOP_VOLANTIS

strat = StratigraphyMapping(
    source_system="rms",
    target_system="smda",
    source_id="TopVOLANTIS",
    target_id="VOLANTIS GP. Top",
    target_uuid=UUID(),
)

"""
mappings:
  - source_system: "rms"
    target_system: "smda"
    mapping_type: "stratigraphy"
    source_id: "TopVOLANTIS"
    target_id: "VOLANTIS GP. Top"
    target_uuid: 1123...
  - source_system: "rms"
    target_system: "smda"
    mapping_type: "stratigraphy"
    source_id: "Top_VOLANTIS"
    target_id: "VOLANTIS GP. Top"
    target_uuid: 1123...
"""

# Next time:
# - FMU-to-FMU mappings (RMS to Eclipse) -- uuid?
# - Different fields for different targets?
#
# - Where is .fmu?
# - .fmu
# - fmuconfig/.static
#
# When ert is running a realization, it expects all the data it needs to be copied to
# the compute node it's working.
#
# .fmu <-- from a compute node, to the node that started an experiment
#
# OR: CaseMetadata copies this data to the scratch disk?


class WellMapping(IdentifierMapping):
    """Represents a mapping from well aliases identifiers to an official
    identifier."""

    mapping_type: Literal[MappingType.well]
    # specific well mapping fields...


class FaultMapping(IdentifierMapping):
    """Represents a mapping from well aliases identifiers to an official
    identifier."""

    mapping_type: Literal[MappingType.well]
    # specific well mapping fields...


# ------------------- Relationship mappings


class EntityReference(BaseModel):
    """Represents one entity we wish to related to naother entity.

    This is typically an object exported by dataio."""

    name: str
    uuid: UUID  # needed?
    content: Content
    relative_path: Path
    absolute_path: Path


# As a Webviz developer, I would link to be able to link a grid property to the grid.

# data.geometry -> relative_path (this is a weak uniqueness guarantee) should be UUID.
# Uniqueness is only within the _case_. The case can only have a single file at any
# given path.


class RelationshipMapping(BaseMapping):
    """Base class for a mapping that represents a relationship between two entities."""

    source_entity: EntityReference
    target_entity: EntityReference
    relation_type: RelationType


class ParentChildMapping(BaseMapping):
    pass


class HierarchicalMapping(RelationshipMapping):
    pass


class Mappings(BaseModel):
    """This collects a list of mappings under a mappings key in metadata or in a file on
    disk.

    mappings:
        - well mapping
        - stratigraphy mapping
        - parent-child mapping

    filter in this list the content type.
    """

    items: List[BaseMapping]


class OrderedMappings(Mappings):
    """Items in this list imply an ordering that is important in some context."""

    ordered: bool = True


class MappingFile(RootModel):
    """mappings.yml for static data"""

    root: Mappings
