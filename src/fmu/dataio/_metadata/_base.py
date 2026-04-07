from abc import ABC, abstractmethod

from pydantic import BaseModel


class Provider(ABC):
    @abstractmethod
    def get_metadata(self) -> BaseModel:
        """Get the Pydantic model of the metadata that a provider is meant
        to provide.

        Returns:
            BaseModel: The Pydantic BaseModel representing metadata.

        Raises:
            InvalidMetadataError: When the derived metadata is invalid.
        """
        raise NotImplementedError
