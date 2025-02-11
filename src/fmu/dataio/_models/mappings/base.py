from enum import Enum
from typing import List, Literal, Union

from pydantic import UUID, BaseModel, RootModel

from fmu.dataio._models.fields import Tracklog

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
    stratigraphy = "stratigraphy"
    well = "well"


class Source(BaseModel):
    name: str  # RMS, Eclipse, ...
    origination: Literal["user", "automatic"]


class BaseMapping(BaseModel):
    """
    mappings:
      ...
      items: [ ]
    """

    source: Source
    target: str  # SMDA
    eventlog: Tracklog  # Some way to follow when static, stored metadata is update


class StandardMapping(BaseMapping):
    """Mapping names"""

    source_name: Union[List[str], str]
    target_name: str
    target_uid: UUID  # type: ignore


class RelationshipMapping(BaseMapping):
    """Stratigraphic elements being mapped"""

    # TODO


class StratigraphyMapping(StandardMapping):
    type: Literal[MappingType.stratigraphy]
    # specific stratigraphy mapping fields ...


class WellMapping(StandardMapping):
    type: Literal[MappingType.well]
    # specific well mapping fields...


class Mappings(BaseModel):
    """This is mappings key in metadata (somewhere)
    mappings:
        - well mapping
        - stratigraphy mapping
        - parent-child mapping

    filter in this list the content type.
    """

    items: List[Union[StratigraphyMapping, WellMapping]]


class MappingFiles(RootModel):
    """mappings.yml for static data"""

    root: Mappings
