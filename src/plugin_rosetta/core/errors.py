"""Package error hierarchy."""


class RosettaError(Exception):
    """Base exception for plugin-rosetta."""


class ConfigurationError(RosettaError):
    """Raised when configuration cannot be loaded or validated."""


class ValidationError(RosettaError):
    """Raised when input does not satisfy a required contract."""


class RosettaIOError(RosettaError):
    """Raised when an input or output operation fails."""
