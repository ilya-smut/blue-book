from bluebook import token_manager
from bluebook.configuration import Configuration
from google import genai
from pathlib import Path
import shutil
from werkzeug.datastructures import FileStorage


class FileManager:
    def __init__(self):
        self.client_init = False
        self.dst_dir = Configuration.SystemPath.FILES_CACHE_PATH
        self.dst_dir.mkdir(exist_ok=True)
        self.init_file_api_client()
    
    def get_path(self, name:str):
        path = Path(self.dst_dir / name)
        if path.exists():
            return path
    
    def init_file_api_client(self):
        config = token_manager.load_config()
        if token_manager.is_token_present(config):
            self._token = config['API_TOKEN']
            self.token_uploaded = True
            self.client = genai.Client(api_key=self._token)
            if self.client:
                self.client_init = True
            else:
                self.client = None
        else:
            self._token = None
            self.client = None
    
    def copy2cache(self, src_path: Path):
        if src_path.exists() and src_path.is_file():
            dst_path = self.dst_dir / src_path.name
            if shutil.copy2(src=src_path, dst=dst_path):
                return dst_path
        else:
            return None
    
    def ls_cache_dir(self, str_names = False):
        files = []
        for file in self.dst_dir.iterdir():
            files.append(file)
        if not str_names:
            return files
        str_names = [f.name for f in files]
        return str_names
    
    def remove_from_cache(self, path_or_name: str|Path):
        if not(type(path_or_name) is Path):
            path_or_name = Path(self.dst_dir / path_or_name)
        path = path_or_name
        Path.unlink(path, missing_ok=True)

    def ls_remote(self):
        if not self.client_init:
            return {}
        files: dict[str, str] = {}
        for f in self.client.files.list():
            files[f.display_name] = f.name
        return files
    
    def get_remote_key(self, name):
        files = self.ls_remote()
        if name in files:
            return files[name]
        else:
            return None
        
    def get_from_remote(self, name: str):
        key = self.get_remote_key(name)
        if key:
            return self.client.files.get(name=key)
        return None
    
    def upload_from_cache(self, name: str, force_unique=False):
        if not name:
            return None
        path = self.get_path(name)
        if not path:
             return None
        if not self.client_init:
            return None
        while name in self.ls_remote():
            if force_unique:
                self.remove_from_remote(name=name)
            else:
                return None
        uploaded = self.client.files.upload(file=path, config={"display_name":name})  
        if uploaded:
            return uploaded
        return None

    def combined_upload(self, src_path: Path, force_unique=False):
        dst_path = self.copy2cache(src_path=src_path)
        return self.upload_from_cache(name=dst_path.name, force_unique=force_unique)
    
    def remove_from_remote(self, name):
        key =self.get_remote_key(name)
        print(key)
        if key:
            self.client.files.delete(name=key)
    
    def form_file2cache(self, file: FileStorage):
        dst_path = self.dst_dir / file.filename
        file.save(dst=dst_path)
        return file.name

