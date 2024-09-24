import warnings
from functools import wraps


def experimental(func):  # type: ignore
    """Decorator to mark functions as experimental."""

    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore
        warnings.warn(
            f"{func.__name__} is experimental and may change in future versions.",
            UserWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper
