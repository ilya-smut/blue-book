import logging
from pathlib import Path
import shutil

from google import genai
from werkzeug.datastructures import FileStorage

from bluebook import token_manager
from bluebook.configuration import Configuration

logger = logging.getLogger("bluebook.file_manager")


class FileManager:
    def __init__(self) -> None:
        self.client_init = False
        self.dst_dir = Configuration.SystemPath.FILES_CACHE_PATH
        self.dst_dir.mkdir(exist_ok=True)
        self.init_file_api_client()

    def _sanitize_filename(self, name: str) -> str:
        """Extract just the filename, preventing directory traversal attacks.
        
        Args:
            name: The filename or path to sanitize.
            
        Returns:
            The sanitized filename without any directory components.
        """
        # Use Path to extract just the filename component
        return Path(name).name

    def get_path(self, name: str) -> Path | None:
        safe_name = self._sanitize_filename(name)
        path = Path(self.dst_dir / safe_name)
        if path.exists():
            return path
        return None
    
    def init_file_api_client(self):
        config = token_manager.load_config()
        if token_manager.is_token_present(config):
            self._token = config['API_TOKEN']
            self.token_uploaded = True
            try:
                self.client = genai.Client(api_key=self._token)
                if self.client:
                    self.client_init = True
                else:
                    self.client = None
            except Exception as e:
                logger.error(f"Failed to initialize Gemini client: {e}")
                self.client = None
                self.client_init = False
        else:
            self._token = None
            self.client = None

    def _ensure_client(self) -> bool:
        """Lazily (re)initialize the Gemini client if not yet ready."""
        if not self.client_init:
            self.init_file_api_client()
        return self.client_init
    
    def copy2cache(self, src_path: Path) -> Path | None:
        if src_path.exists() and src_path.is_file():
            safe_name = self._sanitize_filename(src_path.name)
            dst_path = self.dst_dir / safe_name
            try:
                shutil.copy2(src=src_path, dst=dst_path)
                return dst_path
            except OSError as e:
                logger.error(f"Failed to copy file to cache: {e}")
                return None
        return None
    
    def ls_cache_dir(self, str_names=False):
        files = []
        try:
            for file in self.dst_dir.iterdir():
                files.append(file)
        except Exception as e:
            logger.error(f"Failed to list cache directory: {e}")
            return [] if str_names else files
        
        if not str_names:
            return files
        return [f.name for f in files]
    
    def remove_from_cache(self, path_or_name: str | Path) -> None:
        if isinstance(path_or_name, Path):
            # If it's already a Path, just use the name part
            safe_name = self._sanitize_filename(path_or_name.name)
        else:
            safe_name = self._sanitize_filename(path_or_name)
        path = self.dst_dir / safe_name
        path.unlink(missing_ok=True)

    def ls_remote(self):
        """List files from Gemini API. Returns empty dict on error."""
        if not self._ensure_client():
            return {}
        try:
            files: dict[str, str] = {}
            for f in self.client.files.list():
                files[f.display_name] = f.name
            return files
        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            return {}
    
    def get_remote_key(self, name):
        files = self.ls_remote()
        if name in files:
            return files[name]
        return None
        
    def get_from_remote(self, name: str):
        key = self.get_remote_key(name)
        if key:
            try:
                return self.client.files.get(name=key)
            except Exception as e:
                logger.error(f"Failed to get remote file {name}: {e}")
                return None
        return None
    
    def upload_from_cache(self, name: str, force_unique=False):
        if not name:
            return None
        path = self.get_path(name)
        if not path:
            return None
        if not self._ensure_client():
            return None
        
        try:
            remote_files = self.ls_remote()
            while name in remote_files:
                if force_unique:
                    self.remove_from_remote(name=name)
                    remote_files = self.ls_remote()
                else:
                    return None
            
            uploaded = self.client.files.upload(file=path, config={"display_name": name})
            return uploaded if uploaded else None
        except Exception as e:
            logger.error(f"Failed to upload file {name}: {e}")
            return None

    def combined_upload(self, src_path: Path, force_unique=False):
        dst_path = self.copy2cache(src_path=src_path)
        if dst_path:
            return self.upload_from_cache(name=dst_path.name, force_unique=force_unique)
        return None
    
    def remove_from_remote(self, name):
        key = self.get_remote_key(name)
        if key:
            try:
                self.client.files.delete(name=key)
                logger.debug(f"Deleted remote file: {name}")
            except Exception as e:
                logger.error(f"Failed to delete remote file {name}: {e}")
    
    def form_file2cache(self, file: FileStorage) -> str | None:
        if not file.filename:
            return None
        safe_name = self._sanitize_filename(file.filename)
        dst_path = self.dst_dir / safe_name
        try:
            file.save(dst=dst_path)
            return safe_name
        except OSError as e:
            logger.error(f"Failed to save file to cache: {e}")
            return None