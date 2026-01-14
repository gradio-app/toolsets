from typing import TYPE_CHECKING, Any

from anyio.to_thread import run_sync

if TYPE_CHECKING:
    from mcp import types
    from mcp.server import Server

    from .toolset import Toolset
else:
    try:
        from mcp import types
        from mcp.server import Server
    except ImportError:
        types = None
        Server = None


def create_mcp_server(toolset: "Toolset") -> "Server":
    """
    Create an MCP server that acts as a pass-through for all tools in this toolset.

    Args:
        toolset: The Toolset instance to create the MCP server for.

    Returns:
        The MCP server instance.
    """
    if Server is None:
        raise ImportError(
            "The `mcp` package is required to create an MCP server. "
            "Please install it with: `pip install gradio[mcp]`"
        )

    toolset._get_tool_data()
    server = Server(str(toolset._name or "Toolset"))

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        tools = []
        for tool_name, tool_data in toolset._tool_data.items():
            tools.append(
                types.Tool(
                    name=tool_name,
                    description=tool_data.get("description", ""),
                    inputSchema=tool_data.get("inputSchema", {}),
                )
            )

        has_deferred = bool(toolset._deferred_elements)
        if has_deferred:
            tools.append(
                types.Tool(
                    name="Search Deferred Tools",
                    description="Search for deferred tools using semantic and keyword matching. Returns top matching tools with their names, descriptions, and input schemas.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query to find relevant tools",
                            },
                            "top_k": {
                                "type": "integer",
                                "description": "Number of top results to return",
                                "default": 2,
                            },
                        },
                        "required": ["query"],
                    },
                )
            )
            tools.append(
                types.Tool(
                    name="Call Deferred Tool",
                    description="Call a deferred tool by name with the provided parameters.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "tool_name": {
                                "type": "string",
                                "description": "Name of the deferred tool to call",
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Parameters to pass to the tool",
                            },
                        },
                        "required": ["tool_name", "parameters"],
                    },
                )
            )

        return tools

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        if name == "Search Deferred Tools":
            query = arguments.get("query", "")
            top_k = arguments.get("top_k", 2)
            results = await run_sync(
                lambda: toolset._search_deferred_tools(query, top_k)
            )
            import json

            content = [
                types.TextContent(type="text", text=json.dumps(results, indent=2))
            ]
            return types.CallToolResult(content=content)

        if name == "Call Deferred Tool":
            tool_name = arguments.get("tool_name")
            parameters = arguments.get("parameters", {})
            if not tool_name:
                raise ValueError("tool_name is required")
            if tool_name not in toolset._deferred_tool_to_element:
                raise ValueError(f"Deferred tool '{tool_name}' not found")

            element = toolset._deferred_tool_to_element[tool_name]
            result = await run_sync(lambda: element.execute_tool(tool_name, parameters))

            if result is None:
                content = []
            else:
                content = [types.TextContent(type="text", text=str(result))]

            return types.CallToolResult(content=content)

        if name in toolset._deferred_tool_to_element:
            raise ValueError(
                f"Tool '{name}' is deferred. Use 'Call Deferred Tool' to execute it."
            )

        if name not in toolset._tool_to_element:
            raise ValueError(f"Tool '{name}' not found")

        element = toolset._tool_to_element[name]
        result = await run_sync(lambda: element.execute_tool(name, arguments))

        if result is None:
            content = []
        else:
            content = [types.TextContent(type="text", text=str(result))]

        return types.CallToolResult(content=content)

    return server
