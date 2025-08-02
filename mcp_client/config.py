import os
import yaml


def load_config(path="config.yaml"):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def get_api_key(mcp_id: str):
    return os.getenv(f"{mcp_id.upper()}_API_KEY")