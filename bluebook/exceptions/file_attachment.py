class FileAttachmentError(Exception):
    """Base Exception for all File Attachment related errors."""
    pass


class FileNotFoundError(FileAttachmentError):
    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(f"Attached file {filename} was not found in local cache.")