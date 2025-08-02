### 4. `mcp-client` — Model Context Protocol Client

Requires: OpenAI API key

- **Description:**  
  Client for running agentic inference against MCP/JSON-RPC servers (e.g., Omni, OpenAI).
- **Entrypoint:**  
  CLI: `python -m mcp_client.runner --mcp-id <ID> --query <QUERY>`
- **Configurable Arguments:**
  - `--mcp-id`: MCP server ID (from config).
  - `--query`: Query string.