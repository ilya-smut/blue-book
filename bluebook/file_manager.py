from google import genai  # type: ignore
from pathlib import Path
from typing import Optional


class FileManager:
    def __init__(self, token: str):
        self.client = genai.Client(api_key=token)
    
    def upload_file(self, filepath: Path, name: Optional[str], display_name: Optional[str], mime_type: Optional[str]):
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

