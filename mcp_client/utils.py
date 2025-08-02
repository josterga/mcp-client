import os
import re


def substitute_env_vars(obj):
    """Recursively replace ${VAR_NAME} in dict or string with environment variables."""
    if isinstance(obj, str):
        return re.sub(r"\${(.*?)}", lambda m: os.getenv(m.group(1), ""), obj)
    elif isinstance(obj, dict):
        return {k: substitute_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [substitute_env_vars(i) for i in obj]
    return obj