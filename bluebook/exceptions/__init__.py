"""Exceptions for the Blue Book application.

This package contains custom exceptions organized by module/feature.
"""

from bluebook.exceptions.file_attachment import (
    FileAttachmentError,
    FileCacheError,
    FileNotFoundError,
    FileNotFoundInCacheError,
    FileRetrievalError,
    FileUploadError,
)

__all__ = [
    "FileAttachmentError",
    "FileCacheError",
    "FileNotFoundError",
    "FileNotFoundInCacheError",
    "FileRetrievalError",
    "FileUploadError",
]
