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
    server = Server("gradio/mcp_tools")
    tools = await server._get_tools_async()
    assert isinstance(tools, list)
    assert len(tools) == 3

    server = Server("gradio/mcp_tools", tools=["mcp_tools_prime_factors"])
    tools = await server._get_tools_async()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0]["name"] == "mcp_tools_prime_factors"

    server = Server("gradio/mcp_tools", tools=".*cheetah.*")
    tools = await server._get_tools_async()
    assert isinstance(tools, list)
    assert len(tools) == 1
    assert tools[0]["name"] == "mcp_tools_generate_cheetah_image"
