from __future__ import annotations

from typing import Literal, Optional, Union

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    Field,
    RootModel,
)
from typing_extensions import Annotated

from fmu.dataio._products import InplaceVolumesSchema

from . import enums


class FileSchema(BaseModel):
    """The schema identifying the format of a product."""

    version: str
    """The version of the product schema."""

    url: AnyHttpUrl
    """The url to the product schema."""


class Product(BaseModel):
    """
    The ``product`` field contains information about which product this
    data object represent.
    """

    name: enums.ProductName
    """The identifying product name for this data object."""

    file_schema: Optional[FileSchema] = Field(default=None)
    """The schema identifying the format of the product."""


class InplaceVolumesProduct(Product):
    """
    The ``product`` field contains information about which product this
    data object represent.
    This class contains metadata for the 'inplace_volumes' product.
    """

    name: Literal[enums.ProductName.inplace_volumes]
    """The identifying product name for the 'inplace_volumes' product."""

    file_schema: FileSchema = FileSchema(
        version=InplaceVolumesSchema.VERSION,
        url=AnyHttpUrl(InplaceVolumesSchema.url()),
    )
    """The schema identifying the format of the 'inplace_volumes' product."""


class AnyProduct(RootModel):
    """
    The ``product`` field contains information about which product this data object
    represent. Data that is tagged as a product is a standard result from FMU that
    conforms to a specified standard.

    This class, ``AnyProduct``, acts as a container for different data products, with
    the exact product being identified by the ``product.name`` field.
    """

    root: Annotated[
        Union[InplaceVolumesProduct,],
        Field(discriminator="name"),
    ]
