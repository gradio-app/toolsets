import pytest
from toolsets import Server


def test_server_with_space_id():
    server = Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast")
    assert server.url_or_space == "prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast"
    assert server._mcp_url.endswith("/gradio_api/mcp")


def test_server_with_url():
    url = "https://linoyts-qwen-image-edit-angles.hf.space/gradio_api/mcp/"
    server = Server(url)
    assert server._mcp_url == url.rstrip("/")


def test_server_with_tools_filter():
    server = Server(
        "prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast",
        tools=["tool1", "tool2"]
    )
    assert server.tools == ["tool1", "tool2"]


def test_server_with_regex_filter():
    server = Server(
        "prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast",
        tools="edit.*"
    )
    assert server.tools == "edit.*"


@pytest.mark.asyncio
async def test_server_get_tools():
    server = Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast")
    tools = await server._get_tools_async()
    assert isinstance(tools, list)
    if len(tools) > 0:
        assert "name" in tools[0]
        assert "description" in tools[0]
        assert "inputSchema" in tools[0]

