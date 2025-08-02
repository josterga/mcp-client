class ToolResponse:
    def __init__(self, response_dict):
        self.raw = response_dict
        self.result = response_dict.get("result", {})
        self.content = self.result.get("content", [])
        self.is_error = self.result.get("isError", False)

    def get_text(self):
        if self.content and isinstance(self.content, list):
            return self.content[0].get("text", "")
        return ""

    def to_dict(self):
        return self.result
