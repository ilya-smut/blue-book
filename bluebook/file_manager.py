from google import genai  # type: ignore
from pathlib import Path
import shutil
import base64
import hashlib
from typing import Optional
import logging
from bluebook import configuration

logger = logging.getLogger("bluebook.file_manager")

class UploadedFilesManager:
    def __init__(self, token: str):
        self.client = genai.Client(api_key=token)
    
    def upload_file(self, filepath: Path, name: Optional[str] = None, display_name: Optional[str] = None, mime_type: Optional[str] = None):
        config = {}
        logger.debug("Uploading file..")
        if name:
            logger.debug("Name specified "+name)
            config['name'] = name
        if display_name:
            logger.debug("Display name specified "+display_name)
            config['display_name'] = display_name
        if mime_type:
            logger.debug("Mime type specified "+mime_type)
            config['mime_type'] = mime_type
        if filepath.exists:
            logger.debug("File exists on filesystem")
            self.client.files.upload(file=filepath, config=config)
        else:
            logger.debug("File not found. "+str(filepath))
            raise FileNotFoundError(filepath)
        logger.debug("File uploaded "+str(filepath))

    def list_files(self, as_list = False, names_only=False):
        if names_only:
            files = []
            for file in self.client.files.list():
                files.append({'name': file.name, 'display_name': file.display_name})
            return files

        if as_list:
            return list(self.client.files.list())
        
        return self.client.files.list()
    
    def get_file(self, name: str):
        '''
        Raises FileNotFoundError
        '''
        try:
            file = self.client.files.get(name=name)
            return file
        except:
            raise FileNotFoundError(name)
    
    def delete_file(self, name: str):
        try:
            self.client.files.get(name=name)
            self.client.files.delete(name=name)
        except:
            raise FileNotFoundError(name)
        

class LocalMediaManager:
    def __init__(self):
        self.media_dir = configuration.Configuration.SystemPath.MEDIA_PATH
    
    def base64_sha256(self, filepath: Path, chunk_size: int = 4096) -> str:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as file:
            while True:
                chunk = file.read(chunk_size)
                if not chunk:
                    break
                sha256_hash.update(chunk)
        hex_hash = sha256_hash.hexdigest()
        encoded_hash = base64.b64encode(hex_hash.encode('ascii')).decode('ascii')
        return encoded_hash
    
    def list_local_files(self):
        available_files = []
        for file in self.media_dir.iterdir():
            available_files.append(file.name)
    
    def get_local_filepath(self, name: str | Path):
        full_path = self.media_dir / name
        if full_path.is_file():
            return full_path
        else:
            return None
        
    def copy_file_to_media(self, filepath: Path):
        if filepath.exists() and filepath.is_file():
            if not self.get_local_filepath(filepath.name):
                shutil.copy(filepath, self.media_dir / filepath.name)
            else:
                logger.debug("Did not copy to media - file already exists in media.")
        else:
            logger.debug("Did not copy to media - source not found")
    
    def delete_local_media(self, name: str | Path):
        full_path = self.media_dir / name
        if self.media_dir in full_path.parents and full_path.is_file():   # Prevent directory traversal
            full_path.unlink()
        else:
            raise FileNotFoundError("Could not find "+name+" locally.")


class FileManager:
    def __init__(self, token: str):
        self.local_media_manager = LocalMediaManager()
        self.uploaded_files_manager = UploadedFilesManager(token=token)
    
    def verify_local(self, filepath: Path):
        stem = filepath.stem
        uploaded_file = self.uploaded_files_manager.get_file(stem)
        if not uploaded_file:
            return False
        local_hash = self.local_media_manager.base64_sha256(filepath)
        if not local_hash == uploaded_file.sha256_hash:
            return False
        else:
            return True
    
    def upload_local_file(self, filepath: Path):
        if not (filepath.exists() and filepath.is_file()):
            raise FileNotFoundError(filepath)
        self.local_media_manager.copy_file_to_media(filepath=filepath)
        try:
            self.uploaded_files_manager.upload_file(
                filepath=self.local_media_manager.get_local_filepath(filepath.name),
                name = filepath.stem
            )
        except genai.errors.ClientError:
            logger.debug("Upload failed. Client Error.")

        if not self.verify_local(filepath = self.local_media_manager.get_local_filepath(filepath.name)):
            raise Exception("File upload failed. Hashes do not match")
        
    def delete_file_by_name(self, filename):
        filename_with_appendix = filename+".pdf" # currently only pdfs are allowed for upload. Needs to be changed. Potentially map names in storage.db
        filepath = self.local_media_manager.media_dir / Path(filename_with_appendix)
        logger.debug("Trying to delete "+filename+" | "+str(filepath))
        try:
            self.uploaded_files_manager.delete_file(filename)
            logger.debug("Deleted file from gen ai server")
        except FileNotFoundError:
            logger.debug("File "+filename+" not found on gen-ai server. Could not delete.")
        
        try:
            self.local_media_manager.delete_local_media(filename_with_appendix)
            logger.debug("Deleted file from media dir")
        except FileNotFoundError:
            logger.debug("File "+str(filepath)+" was not found in media dir. Could not delete")
        

