import asyncio
import re
from typing import Any

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.exceptions import McpError

from .toolset_element import ToolsetElement


class MCPConnectionError(Exception):
    """Raised when unable to connect to an MCP server."""

    pass


class MCPServerNotFoundError(Exception):
    """Raised when an MCP server is not found or not enabled."""

    pass


class Server(ToolsetElement):
    def __init__(self, url_or_space: str, tools: list[str] | str | None = None):
        """
        Adds all of the tools from the server to the toolset. The server can be a Gradio Space or any arbitrary MCP server using the Streamable HTTP protocol.

        Args:
            url_or_space (str): The URL of the MCP server (e.g. https://huggingface.co/spaces/username/space-name/gradio_api/mcp) or space name (username/space-name) of the server.
            tools (list[str] | str | None): The tools to add from the server. If None, all tools are added. Invalid tool names are ignored. Instead of a list of tool names, a regular expression can be provided to match tool names.

        Returns:
            Server: The server instance.
        """
        self.url_or_space = url_or_space
        self.tools = tools
        self._mcp_url = self._resolve_mcp_url(url_or_space)
        self._cached_tools: list[dict[str, Any]] | None = None

    @property
    def name(self) -> str:
        return self.url_or_space

    def _resolve_mcp_url(self, url_or_space: str) -> str:
        if url_or_space.startswith("http://") or url_or_space.startswith("https://"):
            url = url_or_space.rstrip("/")
            if not url.endswith("/gradio_api/mcp"):
                return url
            return f"{url}/"

        space_id = url_or_space
        embed_url = f"https://huggingface.co/spaces/{space_id}/embed"

        try:
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                response = client.get(embed_url)
                response.raise_for_status()
                base_url = str(response.url).rstrip("/")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise MCPServerNotFoundError(
                    f"Space '{space_id}' not found on Hugging Face. "
                    "Please check that the space name is correct."
                ) from e
            raise MCPConnectionError(
                f"Error accessing space '{space_id}': HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise MCPConnectionError(
                f"Error connecting to space '{space_id}': {e}"
            ) from e

        return f"{base_url}/gradio_api/mcp/"

    def _filter_tools(self, tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.tools is None:
            return tools

        if isinstance(self.tools, str):
            pattern = re.compile(self.tools)
            return [tool for tool in tools if pattern.search(tool.get("name", ""))]

        tool_names_set = set(self.tools)
        return [tool for tool in tools if tool.get("name") in tool_names_set]

    def _extract_mcp_error(self, exc: Exception) -> Exception | None:
        """Extract McpError from ExceptionGroup if present."""
        if hasattr(exc, "exceptions"):
            for sub_exc in exc.exceptions:
                if isinstance(sub_exc, McpError):
                    return sub_exc
                nested = self._extract_mcp_error(sub_exc)
                if nested:
                    return nested
        elif isinstance(exc, McpError):
            return exc
        return None

    async def _get_tools_async(self) -> list[dict[str, Any]]:
        try:
            async with streamablehttp_client(self._mcp_url) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools_response = await session.list_tools()
                    tools = []
                    for tool in tools_response.tools:
                        tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description or "",
                                "inputSchema": tool.inputSchema,
                            }
                        )

                    return self._filter_tools(tools)
        except Exception as e:
            if isinstance(e, (MCPConnectionError, MCPServerNotFoundError)):
                raise

            mcp_error = self._extract_mcp_error(e)
            if mcp_error:
                error_msg = str(mcp_error)
                if (
                    "Session terminated" in error_msg
                    or "not found" in error_msg.lower()
                ):
                    raise MCPServerNotFoundError(
                        f"Unable to connect to MCP server at '{self._mcp_url}'. "
                        f"The Space '{self.url_or_space}' may not have MCP enabled with Streamable HTTP. "
                        "To enable MCP, launch the Gradio app with `mcp_server=True`."
                    ) from mcp_error
                raise MCPConnectionError(
                    f"Error connecting to MCP server at '{self._mcp_url}': {mcp_error}"
                ) from mcp_error

            if isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code == 404:
                    raise MCPServerNotFoundError(
                        f"MCP server not found at '{self._mcp_url}'. "
                        f"The Space '{self.url_or_space}' may not have MCP enabled. "
                        "To enable MCP, launch the Gradio app with `mcp_server=True`."
                    ) from e
                raise MCPConnectionError(
                    f"HTTP error connecting to MCP server at '{self._mcp_url}': {e.response.status_code}"
                ) from e

            if isinstance(e, httpx.RequestError):
                raise MCPConnectionError(
                    f"Network error connecting to MCP server at '{self._mcp_url}': {e}"
                ) from e

            raise MCPConnectionError(
                f"Unexpected error connecting to MCP server at '{self._mcp_url}': {e}"
            ) from e

    def get_tools(self) -> list[dict[str, Any]]:
        """
        Returns a list of tool names and descriptions from the server.

        Returns:
            list[dict[str, Any]]: A list of tool dictionaries.
        """
        if self._cached_tools is None:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            self._cached_tools = loop.run_until_complete(self._get_tools_async())

        return self._cached_tools

    async def _execute_tool_async(
        self, tool_name: str, parameters: dict[str, Any]
    ) -> Any:
        try:
            async with streamablehttp_client(self._mcp_url) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    result = await session.call_tool(tool_name, arguments=parameters)

                    if result.content and len(result.content) > 0:
                        content = result.content[0]
                        if hasattr(content, "text"):
                            return content.text
                        return str(content)
                    return None
        except Exception as e:
            if isinstance(e, (MCPConnectionError, MCPServerNotFoundError)):
                raise

            mcp_error = self._extract_mcp_error(e)
            if mcp_error:
                error_msg = str(mcp_error)
                if (
                    "Session terminated" in error_msg
                    or "not found" in error_msg.lower()
                ):
                    raise MCPServerNotFoundError(
                        f"Unable to connect to MCP server at '{self._mcp_url}'. "
                        f"The Space '{self.url_or_space}' may not have MCP enabled with Streamable HTTP."
                    ) from mcp_error
                raise MCPConnectionError(
                    f"Error executing tool '{tool_name}' on MCP server: {mcp_error}"
                ) from mcp_error

            if isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code == 404:
                    raise MCPServerNotFoundError(
                        f"MCP server not found at '{self._mcp_url}'. "
                        f"The Space '{self.url_or_space}' may not have MCP enabled."
                    ) from e
                raise MCPConnectionError(
                    f"HTTP error executing tool '{tool_name}': {e.response.status_code}"
                ) from e

            if isinstance(e, httpx.RequestError):
                raise MCPConnectionError(
                    f"Network error executing tool '{tool_name}': {e}"
                ) from e

            raise MCPConnectionError(
                f"Unexpected error executing tool '{tool_name}': {e}"
            ) from e

    def execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> Any:
        """
        Executes a tool on the server.

        Args:
            tool_name (str): The name of the tool to execute.
            parameters (dict[str, Any]): The parameters to pass to the tool.
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._execute_tool_async(tool_name, parameters))
