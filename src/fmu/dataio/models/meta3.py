from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, RootModel


class User(BaseModel):
    id: str = Field(description="User id", examples=["peesv", "jlov"])


class Description(RootModel[List[str]]):
    ...


class FMUTime(BaseModel):
    value: datetime
    label: str = Field(examples=["base", "monitor", "mylabel"])


class Source(RootModel[Literal["fmu"]]):
    ...


class Version(RootModel[Literal["0.9.0"]]):
    ...


class TrackLogEvent(BaseModel):
    datetime: datetime
    user: User
    event: str = Field(examples=["created", "updated"])


class TrackLog(RootModel[List[TrackLogEvent]]):
    ...


class CaseObj(BaseModel):
    ...


class DataObj(BaseModel):
    ...


class Meta(RootModel[Union[CaseObj, DataObj]]):
    ...
