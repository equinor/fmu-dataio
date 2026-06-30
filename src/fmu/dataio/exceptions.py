class DeprecationError(ValueError):
    """Raised when deprecated argument usage is invalid."""


class InvalidMetadataError(Exception):
    """Raised when valid metadata cannot be generated or returned."""


class ValidationError(ValueError, KeyError):
    """Raise error while validating."""

    def __str__(self) -> str:
        """Avoid KeyError repr formatting and preserve readable multiline messages."""
        return Exception.__str__(self)


class ConfigurationError(ValueError):
    pass
