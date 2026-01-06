import httpx
from typing import Dict, Any, List, Optional
import json


class MCPClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _normalize_space_url(self, space_name_or_url: str) -> str:
        if space_name_or_url.startswith("http://") or space_name_or_url.startswith("https://"):
            return space_name_or_url
        if "/" in space_name_or_url:
            return f"https://huggingface.co/spaces/{space_name_or_url}"
        return f"https://huggingface.co/spaces/{space_name_or_url}"

    def get_mcp_schema(self, space_name_or_url: Optional[str] = None) -> Dict[str, Any]:
        url = self.base_url
        if space_name_or_url:
            url = self._normalize_space_url(space_name_or_url)

        endpoints = [
            f"{url}/gradio_api/mcp/schema",
            f"{url}/api/mcp/schema",
            f"{url}/mcp/schema"
        ]

        last_error = None
        for endpoint in endpoints:
            try:
                response = self.client.get(endpoint)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                last_error = e
                continue

        raise ConnectionError(f"Failed to fetch MCP schema from {url}. Tried: {endpoints}. Last error: {last_error}")

    def get_tools(self, space_name_or_url: Optional[str] = None) -> List[Dict[str, Any]]:
        schema = self.get_mcp_schema(space_name_or_url)
        tools = schema.get("tools", [])
        return tools

    def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        space_name_or_url: Optional[str] = None
    ) -> Any:
        url = self.base_url
        if space_name_or_url:
            url = self._normalize_space_url(space_name_or_url)

        endpoints = [
            f"{url}/gradio_api/mcp/call",
            f"{url}/api/mcp/call",
            f"{url}/mcp/call"
        ]

        payload = {
            "name": tool_name,
            "arguments": arguments
        }

        last_error = None
        for endpoint in endpoints:
            try:
                response = self.client.post(endpoint, json=payload)
                response.raise_for_status()
                result = response.json()
                return result.get("content", result)
            except httpx.HTTPError as e:
                last_error = e
                continue

        raise RuntimeError(f"Failed to execute tool {tool_name} on {url}. Tried: {endpoints}. Last error: {last_error}")

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

