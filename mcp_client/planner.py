import json
import logging

class QueryPlanner:
    def __init__(self, openai_client):
        if openai_client is None:
            raise Exception("OpenAI client is not set. Please provide an OpenAI client instance.")
        self.openai_client = openai_client
        self.logger = logging.getLogger("mcp_client.planner")

    def plan(self, user_query: str, tools: dict):
        tool_descriptions = []
        tool_examples = []
        for tool in tools.values():
            arg_descs = []
            arg_examples = []
            input_schema = tool.get('inputSchema', {})
            properties = input_schema.get('properties', {})
            required = set(input_schema.get('required', []))
            for arg, spec in properties.items():
                arg_type = spec.get('type', 'string')
                is_required = "required" if arg in required else "optional"
                arg_descs.append(f'  - {arg} ({arg_type}, {is_required})')
                arg_examples.append(f'"{arg}": <{arg_type}>')
            tool_descriptions.append(
                f"- {tool['name']}:\n    Description: {tool['description']}\n    Arguments:\n" + "\n".join(arg_descs)
            )
            tool_examples.append(f'{{"tool": "{tool["name"]}", "args": {{{", ".join(arg_examples)}}}}}')
        tool_list_str = "\n".join(tool_descriptions)
        example_plan = "[\n  " + ",\n  ".join(tool_examples) + "\n]"

        prompt = f"""
        You are an agent with access to the following tools:
        {tool_list_str}

        Given the user query: \"{user_query}\"

        Decompose the task into a sequence of tool calls, specifying the tool name and arguments for each step.

        Instructions:
        - For each tool call, include a unique 'id' field (e.g., 'step1', 'step2', ...).
        - Specify the 'tool' to use and an 'args' object for its arguments.
        - If a tool call depends on the output of a previous step, reference it as '<output from stepID>' in the relevant argument.
        - Return a flat JSON array. Only output valid JSON.

        Example:
        [
          {{"id": "step1", "tool": "tool-a", "args": {{"arg1": "value"}}}},
          {{"id": "step2", "tool": "tool-b", "args": {{"arg2": "<output from step1>"}}}}
        ]
        """

        self.logger.info("Sending tool planning prompt", extra={"user_query": user_query})
        resp = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = resp.choices[0].message.content.strip()

        if content.startswith("```"):
            content = content.split('\n', 1)[-1]
            if content.endswith("```"):
                content = content.rsplit("```", 1)[0].strip()

        try:
            return json.loads(content)
        except Exception as e:
            self.logger.error("Failed to parse tool plan JSON", extra={"content": content, "error": str(e)})
            raise
