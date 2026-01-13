import pytest

from toolsets import Server


def test_server_with_space_id():
    server = Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast")
    assert server.url_or_space == "prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast"
    assert server._mcp_url.endswith("/gradio_api/mcp/")


def test_server_with_url():
    url = "https://linoyts-qwen-image-edit-angles.hf.space/gradio_api/mcp/"
    server = Server(url)
    assert server._mcp_url == url


@pytest.mark.asyncio
async def test_server_get_tools():
    server = Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast")
    tools = await server._get_tools_async()
    assert isinstance(tools, list)
    if len(tools) > 0:
        assert "name" in tools[0]
        assert "description" in tools[0]
        assert "inputSchema" in tools[0]
        
        tool_name = tools[0]["name"]
        
        server_with_tool = Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast", tools=[tool_name])
        filtered_tools = await server_with_tool._get_tools_async()
        assert isinstance(filtered_tools, list)
        assert len(filtered_tools) == 1
        assert filtered_tools[0]["name"] == tool_name
        
        server_with_regex = Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast", tools=f".*{tool_name}.*")
        regex_filtered_tools = await server_with_regex._get_tools_async()
        assert isinstance(regex_filtered_tools, list)
        assert len(regex_filtered_tools) >= 1
        assert any(tool["name"] == tool_name for tool in regex_filtered_tools)