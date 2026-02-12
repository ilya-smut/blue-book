"""Exceptions for file attachment operations.

This module defines exceptions that can occur during file attachment,
upload, and retrieval operations.
"""


class FileAttachmentError(Exception):
    """Base Exception for all File Attachment related errors."""
    
    def __init__(self, message: str = "File attachment error occurred") -> None:
        self.message = message
        super().__init__(message)


class FileNotFoundInCacheError(FileAttachmentError):
    """Raised when a file is not found in the local cache."""
    
    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"File '{filename}' was not found in local cache.")


class FileUploadError(FileAttachmentError):
    """Raised when a file upload to remote storage fails."""
    
    def __init__(self, filename: str, reason: str = "") -> None:
        self.filename = filename
        self.reason = reason
        message = f"Failed to upload file '{filename}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class FileRetrievalError(FileAttachmentError):
    """Raised when retrieving a file from remote storage fails."""
    
    def __init__(self, filename: str, reason: str = "") -> None:
        self.filename = filename
        self.reason = reason
        message = f"Failed to retrieve file '{filename}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class FileCacheError(FileAttachmentError):
    """Raised when a cache operation fails."""
    
    def __init__(self, filename: str, operation: str = "cache") -> None:
        self.filename = filename
        self.operation = operation
        super().__init__(f"Failed to {operation} file '{filename}' in cache.")


# Legacy alias for backwards compatibility
# Note: This shadows the built-in FileNotFoundError, but is kept for compatibility
class FileNotFoundError(FileNotFoundInCacheError):  # noqa: A001
    """Legacy alias for FileNotFoundInCacheError. Use FileNotFoundInCacheError instead."""
    pass