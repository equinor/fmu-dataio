class DeprecationError(ValueError):
    """Raised when deprecated argument usage is invalid."""


class InvalidMetadataError(Exception):
    """Raised when valid metadata cannot be generated or returned."""


class ValidationError(ValueError, KeyError):
    """Raise error while validating."""


class ConfigurationError(ValueError):
    pass
