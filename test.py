from mcp_client.registry import MCPRegistry
import openai

# Optionally, load environment variables if needed
from dotenv import load_dotenv
load_dotenv()

openai_client = openai.OpenAI()  # 
# Initialize the registry and client
registry = MCPRegistry()
client = registry.get_client("Omni", openai_client=openai_client)  # or any MCP id from your config

# Run an agentic inference
result = client.run_agentic_inference("Show me weekly active users trend")

print("Final Answer:", result["answer"])
print("Reasoning Steps:")
for step in result["reasoning_steps"]:
    print(f"Step {step['id']} ({step['tool']}): {step['response']}")