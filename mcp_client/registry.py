from mcp_client.client import MCPClient
from mcp_client.utils import substitute_env_vars
import yaml
import os

class MCPRegistry:
    def __init__(self, config_path="config.yaml"):
        self.configs = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                raw_cfg = yaml.safe_load(f)
            for mcp in raw_cfg.get("mcps", []):
                mcp_id = mcp["id"]
                self.configs[mcp_id] = substitute_env_vars(mcp)

    def get_client(self, mcp_id, openai_client=None, **overrides):
        cfg = self.configs.get(mcp_id, {}).copy()  # Use empty dict if not found
        # Apply overrides
        for key, value in overrides.items():
            if value is not None:
                cfg[key] = value
        # Handle headers merging
        headers = cfg.get("headers", {}).copy()
        if "headers" in overrides and overrides["headers"]:
            headers.update(overrides["headers"])
        cfg["headers"] = headers
        api_key = headers.get("Authorization", "").replace("Bearer ", "")
        return MCPClient(
            base_url=cfg.get("url"),
            api_key=api_key,
            headers=cfg.get("headers", {}),
            metadata=cfg.get("metadata", {}),
            openai_client=openai_client
        )