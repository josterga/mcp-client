import uuid
import json
import requests
import logging
from mcp_client.schemas import ToolResponse
from mcp_client.planner import QueryPlanner

class MCPClient:
    def __init__(self, base_url, api_key, headers=None, metadata=None, openai_client=None):
        self.base_url = base_url
        self.api_key = api_key
        self.custom_headers = headers or {}
        self.metadata = metadata or {}
        self.openai_client = openai_client
        self.tool_cache = None
        self.logger = logging.getLogger("mcp_client")
        self.planner = QueryPlanner(openai_client)

    def _headers(self):
        headers = {
        "Content-Type": "application/json"
        }
        headers.update(self.custom_headers)  # config headers (including Accept, Authorization, etc.)
        return headers


    def _post(self, payload, stream=False):
        headers = self._headers()
        return requests.post(self.base_url, headers=self._headers(), json=payload, stream=stream)

    def initialize(self):
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "1.0",
                "capabilities": {},
                "clientInfo": {"name": "mcp-client", "version": "1.0"}
            }
        }
        try:
            response = self._post(payload)
            if response.status_code != 200:
                raise Exception(f"Initialization failed: {response.status_code}")
        except Exception as e:
            self.logger.error("Failed to initialize MCP", extra={"error": str(e)})
            raise

    def list_tools(self):
        if self.tool_cache:
            return self.tool_cache
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        print("[DEBUG] Sending tools/list request with payload:", payload)
        response = self._post(payload)
        print("[DEBUG] tools/list response status:", response.status_code)
        print("[DEBUG] tools/list response headers:", response.headers)
        print("[DEBUG] tools/list response content:", response.text)
        if response.status_code != 200:
            raise Exception(f"Failed to list tools: {response.status_code} {response.text}")
        try:
            data = self._parse_mcp_response(response)
        except Exception as e:
            print(f"[DEBUG] Failed to parse MCP response in list_tools: {e}\nRaw response: {response.text}")
            raise Exception(f"Failed to parse MCP response in list_tools: {e}\nRaw response: {response.text}")
        self.tool_cache = {tool['name']: tool for tool in data['result']['tools']}
        return self.tool_cache

    def _parse_mcp_response(self, response):
        # Handles both SSE and plain JSON
        if "data: " in response.text:
            json_str = response.text.split("data: ", 1)[1]
            return json.loads(json_str)
        else:
            return response.json()

    def _call_tool(self, tool_name, args, stream=False):
        merged_args = {**getattr(self, "params", {}), **args}
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": merged_args
            }
        }
        print(f"[DEBUG] Calling tool: {tool_name} with args: {merged_args}")
        print(f"[DEBUG] Payload: {payload}")
        response = self._post(payload, stream=stream)
        print("[DEBUG] Tool call response status:", response.status_code)
        print("[DEBUG] Tool call response headers:", response.headers)
        print("[DEBUG] Tool call response content:", response.text)
        if response.status_code != 200:
            print(f"[DEBUG] Non-200 status code: {response.status_code}")
            raise Exception(f"Tool call failed: {response.status_code} {response.text}")
        try:
            return ToolResponse(self._parse_mcp_response(response))
        except Exception as e:
            print(f"[DEBUG] Failed to parse MCP response: {e}\nRaw response: {response.text}")
            raise Exception(f"Failed to parse MCP response: {e}\nRaw response: {response.text}")

    def _resolve_references(self, args, step_outputs):
        for k, v in args.items():
            if isinstance(v, str) and v.startswith("<output from ") and v.endswith(">"):
                ref_id = v[len("<output from "):-1].strip()
                if ref_id not in step_outputs:
                    raise ValueError(f"Referenced step id '{ref_id}' not found in previous outputs.")
                ref_output = step_outputs[ref_id]
                try:
                    parsed = json.loads(ref_output)
                    if isinstance(parsed, dict) and k in parsed:
                        args[k] = parsed[k]
                    elif isinstance(parsed, dict) and len(parsed) == 1:
                        args[k] = next(iter(parsed.values()))
                    else:
                        args[k] = parsed
                except Exception:
                    args[k] = ref_output
        return args

    def run_agentic_inference(self, prompt, stream=False):
        self.initialize()
        tools = self.list_tools()
        plan = self.planner.plan(prompt, tools)
        print("[DEBUG] Plan:", plan)
        context = {}
        step_outputs = {}
        reasoning_steps = []

        for step in plan:
            print(f"[DEBUG] Executing step: {step}")
            step_id = step["id"]
            tool_name = step["tool"]
            args = step["args"].copy()

            args = self._resolve_references(args, step_outputs)

            self.logger.info("Calling tool", extra={"step_id": step_id, "tool": tool_name, "args": args})
            try:
                result = self._call_tool(tool_name, args, stream=stream)
                output_text = result.get_text()
                step_outputs[step_id] = output_text
                reasoning_steps.append({
                    "id": step_id,
                    "tool": tool_name,
                    "args": args,
                    "response": output_text[:300]
                })
            except Exception as e:
                self.logger.error("Tool call failed", extra={"tool": tool_name, "error": str(e)})
                return {
                    "answer": f"[Tool call failed: {tool_name}]",
                    "reasoning_steps": reasoning_steps
                }

        synthesis_prompt = self._synthesize_prompt(prompt, plan, step_outputs)
        try:
            completion = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an assistant synthesizing answers from tool results."},
                    {"role": "user", "content": synthesis_prompt}
                ],
                temperature=0.3,
                max_tokens=800
            )
            return {
                "answer": completion.choices[0].message.content.strip(),
                "reasoning_steps": reasoning_steps
            }
        except Exception as e:
            return {
                "answer": f"[Synthesis failed: {e}]",
                "reasoning_steps": reasoning_steps
            }

    def _synthesize_prompt(self, user_query, plan, step_outputs):
        plan_md = "\n".join([
            f"- {step['tool']}({', '.join(f'{k}={v}' for k, v in step['args'].items())})" for step in plan
        ])
        results_md = "\n".join([
            f"Step {k}: {v}" for k, v in step_outputs.items()
        ])
        return f"""
User question:
{user_query}

Plan:
{plan_md}

Results:
{results_md}

Provide a clear and concise answer using only the information above.
"""
