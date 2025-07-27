from google import genai  # type: ignore
from pathlib import Path
import shutil
import base64
import hashlib
from typing import Optional
from bluebook import configuration


class UploadedFilesManager:
    def __init__(self, token: str):
        self.client = genai.Client(api_key=token)
    
    def upload_file(self, filepath: Path, name: Optional[str] = None, display_name: Optional[str] = None, mime_type: Optional[str] = None):
        config = {}
        if name:
            config['name'] = name
        if display_name:
            config['display_name'] = display_name
        if mime_type:
            config['mime_type'] = mime_type
        if filepath.exists:
            self.client.files.upload(file=filepath, config=config)
        else:
            return FileNotFoundError(filepath)

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
        if file:=self.client.files.get(name=name):
            return file
        else:
            return FileNotFoundError(name)
    
    def delete_file(self, name: str):
        if file:=self.client.files.get(name=name):
            self.client.files.delete(name=name)
        else:
            return FileNotFoundError(name)
        

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
    
    def delete_local_media(self, name: str | Path):
        full_path = self.media_dir / name
        if self.media_dir in full_path.parents() and full_path.is_file():   # Prevent directory traversal
            full_path.unlink()

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
            return FileNotFoundError
        self.local_media_manager.copy_file_to_media(filepath=filepath)
        try:
            self.uploaded_files_manager.upload_file(
                filepath=self.local_media_manager.get_local_filepath(filepath.name),
                name = filepath.stem
            )
        except genai.errors.ClientError:
            pass

        if not self.verify_local(filepath = self.local_media_manager.get_local_filepath(filepath.name)):
            return Exception("File upload failed. Hashes do not match")
