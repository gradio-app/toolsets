import asyncio
from typing import Dict, Any, List, Optional
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def normalize_space_url(space_name_or_url: str) -> str:
    if space_name_or_url.startswith("http://") or space_name_or_url.startswith("https://"):
        url = space_name_or_url.rstrip("/")
        if not url.endswith("/gradio_api/mcp"):
            if url.endswith("/gradio_api/mcp/"):
                return url.rstrip("/")
            return f"{url}/gradio_api/mcp"
        return url
    if "/" in space_name_or_url:
        base_url = f"https://huggingface.co/spaces/{space_name_or_url}"
    else:
        base_url = f"https://huggingface.co/spaces/{space_name_or_url}"
    return f"{base_url}/gradio_api/mcp"


async def get_mcp_tools_async(url_or_space: str) -> List[Dict[str, Any]]:
    mcp_url = normalize_space_url(url_or_space)
    
    async with streamablehttp_client(mcp_url) as (read_stream, write_stream, _):
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
            return tools


async def execute_tool_async(url_or_space: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    mcp_url = normalize_space_url(url_or_space)
    
    async with streamablehttp_client(mcp_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            result = await session.call_tool(tool_name, arguments=arguments)
            
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                return str(content)
            return None


def get_mcp_tools(url_or_space: str) -> List[Dict[str, Any]]:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(get_mcp_tools_async(url_or_space))


def execute_tool(url_or_space: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(execute_tool_async(url_or_space, tool_name, arguments))
