import os
import json
from pathlib import Path

class PathConfig:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_file = self.project_root / "config" / "paths.json"
        self._load_config()

    def _load_config(self):
        if self.config_file.exists():
            with open(self.config_file) as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def get_path(self, key, default=None):
        return self.config.get(key, default)

    def resolve_path(self, path_str):
        if path_str.startswith("~/"):
            return Path.home() / path_str[2:]
        elif path_str.startswith("./"):
            return self.project_root / path_str[2:]
        return Path(path_str)