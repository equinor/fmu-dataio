from __future__ import annotations

from pprint import pp
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from yaml import safe_load


class SMDAAttribute(BaseModel):
    short_identifier: str | None = None
    identifier: str | None = None
    uuid: UUID = Field(title="...", description="....")


class SMDA(BaseModel):
    country: list[SMDAAttribute]
    discovery: list[SMDAAttribute]
    field: list[SMDAAttribute]
    coordinate_system: SMDAAttribute
    stratigraphic_column: SMDAAttribute


class Masterdata(BaseModel):
    smda: SMDA


class Asset(BaseModel):
    name: str


class SSDL(BaseModel):
    access_level: Literal["internal", "external"]
    rep_include: bool


class Access(BaseModel):
    asset: Asset
    ssdl: SSDL


class Model(BaseModel):
    name: str
    revision: str = Field(pattern=r"^\d+\.\d+.\d+\.(dev|prod)$")


class StratigraphyAttribute(BaseModel):
    stratigraphic: bool
    name: str
    alias: list[str] = []
    stratigraphic_alias: list[str] = []


class RMS(BaseModel):
    horizons: dict[str, list[str]]
    zones: dict[str, list[str]]


class Root(BaseModel):
    masterdata: Masterdata
    access: Access
    model: Model
    stratigraphy: dict[str, StratigraphyAttribute]
    global_: dict[str, str | float | int] = Field(alias="global")
    rms: RMS


pp(
    safe_load(
        open(
            "examples/s/d/nn/xcase/realization-1/iter-0/fmuconfig/output/global_variables.yml"
        )
    )
)

m = Root.model_validate(
    safe_load(
        open(
            "examples/s/d/nn/xcase/realization-1/iter-0/fmuconfig/output/global_variables.yml"
        )
    )
)
pp(m.rms)
