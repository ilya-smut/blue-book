from bluebook import database_manager, file_manager
from bluebook.exceptions.file_attachment import FileNotFoundError
import logging

logger = logging.getLogger("bluebook.helpers.file_attachment")

def get_remote_attached_files(db: database_manager.Database, fl: file_manager.FileManager):
    local_attached = db.select_attached_files()
    if not local_attached:
        return []
    filenames_attached = [attached_file['name'] for attached_file in local_attached]
    filenames_in_cache = fl.ls_cache_dir(str_names=True)
    already_in_remote = set(fl.ls_remote().keys())
    not_found_in_cache = set(filenames_attached) - set(filenames_in_cache)
    if not_found_in_cache:
        logger.debug(f"Some attached files were not found in cache. {not_found_in_cache}")
        logger.debug(f"Searching for every missing file in remote...")
        for filename in list(not_found_in_cache):
            logger.debug(f"Looking for {filename}...")
            if not (filename in already_in_remote):
                logger.debug(f"{filename} was NOT found.")
                raise FileNotFoundError(filename=list(not_found_in_cache)[0])
            else:
                logger.debug("Found.")
    not_yet_uploaded = set(filenames_attached) - already_in_remote
    if not_yet_uploaded:
        logger.debug(f"Some attached files were not yet uploaded to remote. Uploading... {not_yet_uploaded}")
        files_to_upload = list(not_yet_uploaded)
        for filename in files_to_upload:
            fl.upload_from_cache(filename, force_unique=True)
            logger.debug(f"File {filename} was uploaded.")
    logger.debug("Starting obtaining remote file handles...")
    remote_files = []
    for filename in filenames_attached:
        remote_file = fl.get_from_remote(name=filename)
        if remote_file:
            remote_files.append(remote_file)
            logger.debug(f"Obtained {filename}")
        else:
            logger.debug(f"Could not obtain {filename}")
    return remote_files

