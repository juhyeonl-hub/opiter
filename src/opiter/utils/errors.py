"""Custom exception types raised by opiter modules."""


class OpiterError(Exception):
    """Base class for all opiter-specific exceptions."""


class CorruptedPDFError(OpiterError):
    """The PDF file is malformed, truncated, or otherwise unreadable."""


class EncryptedPDFError(OpiterError):
    """The PDF requires a password to open."""


class UnsupportedFormatError(OpiterError):
    """The file is not a supported document format."""
