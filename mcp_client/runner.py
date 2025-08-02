from dotenv import load_dotenv
load_dotenv()
import argparse
import openai
from mcp_client.registry import MCPRegistry

def main():
    parser = argparse.ArgumentParser(description="Run MCP client inference")
    parser.add_argument("--mcp-id", required=True, help="MCP server ID from config.yaml")
    parser.add_argument("--query", required=True, help="Query to run")
    args = parser.parse_args()

    # Initialize OpenAI client (API key is read from OPENAI_API_KEY env var)
    openai_client = openai.OpenAI()  # For openai>=1.0.0
    # For openai<1.0.0, use: openai.api_key = os.getenv("OPENAI_API_KEY")

    registry = MCPRegistry()
    client = registry.get_client(args.mcp_id, openai_client=openai_client)
    result = client.run_agentic_inference(args.query)

    print("\n=== Final Answer ===\n")
    print(result["answer"])
    print("\n=== Reasoning Steps ===\n")
    for step in result["reasoning_steps"]:
        print(f"Step {step['id']} ({step['tool']}): {step['response']}")

if __name__ == "__main__":
    main()