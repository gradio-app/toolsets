import asyncio
import re
import httpx
from typing import List, Optional, Dict, Any
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from .toolset_element import ToolsetElement


class Server(ToolsetElement):
    def __init__(self, url_or_space: str, tools: Optional[List[str] | str] = None):
        """
        Adds all of the tools from the server to the toolset. The server can be a Gradio Space or any arbitrary MCP server using the Streamable HTTP protocol.

        Args:
            url_or_space (str): The URL of the MCP server (e.g. https://huggingface.co/spaces/username/space-name/gradio_api/mcp) or space name (username/space-name) of the server.
            tools (Optional[List[str] | str]): The tools to add from the server. If None, all tools are added. Invalid tool names are ignored. Instead of a list of tool names, a regular expression can be provided to match tool names.

        Returns:
            Server: The server instance.
        """
        self.url_or_space = url_or_space
        self.tools = tools
        self._mcp_url = self._resolve_mcp_url(url_or_space)
        self._cached_tools: Optional[List[Dict[str, Any]]] = None

    def _resolve_mcp_url(self, url_or_space: str) -> str:
        if url_or_space.startswith("http://") or url_or_space.startswith("https://"):
            return url_or_space.rstrip("/")

        space_id = url_or_space
        embed_url = f"https://huggingface.co/spaces/{space_id}/embed"

        with httpx.Client(follow_redirects=True) as client:
            response = client.get(embed_url)
            response.raise_for_status()
            base_url = str(response.url).rstrip("/")

        return f"{base_url}/gradio_api/mcp"

    def _filter_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if self.tools is None:
            return tools

        if isinstance(self.tools, str):
            pattern = re.compile(self.tools)
            return [tool for tool in tools if pattern.search(tool.get("name", ""))]

        tool_names_set = set(self.tools)
        return [tool for tool in tools if tool.get("name") in tool_names_set]

    async def _get_tools_async(self) -> List[Dict[str, Any]]:
        async with streamablehttp_client(self._mcp_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_response = await session.list_tools()
                tools = []
                for tool in tools_response.tools:
                    tools.append({
                        "name": tool.name,
                        "description": tool.description or "",
                        "inputSchema": tool.inputSchema
                    })

                return self._filter_tools(tools)

    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Returns a list of tool names and descriptions from the server.

        Returns:
            List[Dict[str, Any]]: A list of tool dictionaries.
        """
        if self._cached_tools is None:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._cached_tools = loop.run_until_complete(self._get_tools_async())

        return self._cached_tools

    async def _execute_tool_async(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        async with streamablehttp_client(self._mcp_url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                result = await session.call_tool(tool_name, arguments=parameters)

                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        return content.text
                    return str(content)
                return None

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Executes a tool on the server.

        Args:
            tool_name (str): The name of the tool to execute.
            parameters (Dict[str, Any]): The parameters to pass to the tool.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._execute_tool_async(tool_name, parameters))
