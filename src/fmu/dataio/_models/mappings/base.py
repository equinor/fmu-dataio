from enum import Enum
from pathlib import Path
from typing import List, Literal, Union
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

    source_system: Source
    target_system: Literal["smda"]
    mapping_type: MappingType


# ------------------- Standard mappings


class StandardMapping(BaseMapping):
    """Base class for a one-to-one or many-to-one mapping of identifiers.

    This mapping represents takes some identifier from one source and correlates it to
    an identifier in a target. Most often this target will be some official masterdata
    store like SMDA."""

    fmu_id: Union[List[str], str]  # FMU name(s)
    target_id: str
    target_uid: UUID


class StratigraphyMapping(StandardMapping):
    """Represents a mapping from stratigraphic aliases identifiers to an official
    identifier."""

    mapping_type: Literal[MappingType.stratigraphy]
    # specific stratigraphy mapping fields ...


class WellMapping(StandardMapping):
    """Represents a mapping from well aliases identifiers to an official
    identifier."""

    mapping_type: Literal[MappingType.well]
    # specific well mapping fields...


class EntityReference(BaseModel):
    """Represents one entity we wish to related to naother entity.

    This is typically an object exported by dataio."""

    name: str
    uuid: UUID  # needed?
    content: Content
    relative_path: Path
    absolute_path: Path


# ------------------- Relationship mappings


class RelationshipMapping(BaseMapping):
    """Base class for a mapping that represents a relationship between two entities."""

    source_entity: EntityReference
    target_entity: EntityReference
    relation_type: RelationType


class ParentChildMapping(BaseMapping):
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


class MappingFile(RootModel):
    """mappings.yml for static data"""

    root: Mappings
