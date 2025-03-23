import os
import sys

import toml

CONFIG_PATH = os.path.expanduser("~/.unchaos/config.toml")

class Config:
    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.config = self.load_config()

    def load_config(self):
        """Load the configuration file, applying defaults if missing."""
        if os.path.exists(self.path):
            try:
                return toml.load(self.path)
            except Exception as e:
                print(f"⚠️ Error loading config file: {e}")
        else:
            print(f"⚠️ Config file not found at {self.path}. Did you forget to run `unchaos init`?")
        sys.exit(1)

    def save_config(self):
        """Save the current config to the file."""
        with open(self.path, "w") as f:
            toml.dump(self.config, f)

    def get(self, key_path, default=None):
        """Get a config value using a dotted key path (e.g., 'storage.database')."""
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            value = value.get(key, {})
        return value if value else default

    def set(self, key_path, value):
        """Set a config value using a dotted key path."""
        keys = key_path.split(".")
        d = self.config
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value
        self.save_config()

# Global config instance
config = Config()