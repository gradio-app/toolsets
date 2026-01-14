import contextlib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

import gradio as gr
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from .mcp_server import create_mcp_server

if TYPE_CHECKING:
    from mcp.server import Server
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

    from .toolset import Toolset
else:
    try:
        from mcp.server import Server
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    except ImportError:
        Server = None
        StreamableHTTPSessionManager = None


def launch_gradio_ui(toolset: "Toolset", mcp_server: bool = False) -> None:
    """
    Launch the Gradio UI for the toolset.

    Args:
        toolset: The Toolset instance to create the UI for.
        mcp_server: If True, create and integrate the MCP server. Defaults to False.
    """
    toolset._get_tool_data()
    if toolset._verbose:
        message = f"\n* Launching Toolset UI and MCP server with ({len(toolset._tool_data)}) tools. "
        if toolset._deferred_elements:
            message += f"Additional deferred tools are available via tool search."
        print(message, "\n")
    if toolset._deferred_elements:
        try:
            toolset._embed_deferred_tools()
        except ImportError as e:
            import warnings

            warnings.warn(
                f"Failed to load sentence-transformers for deferred tools: {e}. "
                "Deferred tools search will not be available. "
                "Install with: pip install toolsets[deferred] or pip install sentence-transformers"
            )

    css = ".tool-item { cursor: pointer; }"

    with gr.Blocks() as demo:
        header_html = "<div style='display: flex; justify-content: space-between; align-items: center;'>"
        if toolset._name:
            header_html += f"<h1 style='margin: 0;'>{toolset._name}</h1>"
        header_html += "<img src='https://raw.githubusercontent.com/abidlabs/toolsets/main/logo.png' style='height: 3.5em; margin-left: auto; width: auto;'>"
        header_html += "</div>"
        gr.HTML(header_html)
        j = gr.JSON(label="inputSchema", value={}, render=False)

        has_deferred = bool(toolset._deferred_elements)

        with gr.Tab(f"Base tools ({len(toolset._tool_data)})"):
            with gr.Row():
                with gr.Column():
                    for tool_name, tool_data in toolset._tool_data.items():
                        h = gr.HTML(
                            f"<p><code>{tool_name}</code></p><p>{tool_data['description']}</p>",
                            container=True,
                            elem_classes="tool-item",
                        )

                        def make_click_handler(schema):
                            return lambda: schema

                        h.click(make_click_handler(tool_data["inputSchema"]), outputs=j)

                    if has_deferred:
                        search_tool_data = {
                            "description": "Search for deferred tools using semantic and keyword matching.",
                            "inputSchema": {
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
                        }
                        h_search = gr.HTML(
                            f"<p><code>Search Deferred Tools</code></p><p>{search_tool_data['description']}</p>",
                            container=True,
                            elem_classes="tool-item",
                        )
                        h_search.click(
                            make_click_handler(search_tool_data["inputSchema"]),
                            outputs=j,
                        )

                        call_tool_data = {
                            "description": "Call a deferred tool by name with the provided parameters.",
                            "inputSchema": {
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
                        }
                        h_call = gr.HTML(
                            f"<p><code>Call Deferred Tool</code></p><p>{call_tool_data['description']}</p>",
                            container=True,
                            elem_classes="tool-item",
                        )
                        h_call.click(
                            make_click_handler(call_tool_data["inputSchema"]),
                            outputs=j,
                        )

                with gr.Column():
                    j.render()

        if has_deferred:
            with gr.Tab("Deferred Tools Search"):
                search_query = gr.Textbox(
                    label="Search Query",
                    placeholder="Enter a search query to find relevant deferred tools...",
                )
                top_k_slider = gr.Slider(
                    minimum=1,
                    maximum=20,
                    value=2,
                    step=1,
                    label="Number of results (top_k)",
                )
                search_results = gr.JSON(label="Search Results")
                search_button = gr.Button("Search", variant="primary")

                def search_deferred(query: str, top_k: int):
                    if not query:
                        return []
                    results = toolset._search_deferred_tools(query, top_k=top_k)
                    return results

                search_button.click(
                    search_deferred,
                    inputs=[search_query, top_k_slider],
                    outputs=search_results,
                )
        else:
            with gr.Tab("Tool search (disabled)"):
                gr.Markdown(
                    "The `tool_search` tool is only enabled if you add a tool with `defer_loading=True`."
                )

        with gr.Tab("MCP Info"):
            mcp_url = gr.Textbox(
                label="MCP URL (Streamable HTTP transport).", buttons=["copy"]
            )
            mcp_config = gr.JSON(label="MCP Configuration", value={})
            gr.Markdown(
                "This MCP server was created with the [toolsets](https://github.com/abidlabs/toolsets) library."
            )

        def get_mcp_info(request: gr.Request):
            base_url = f"{request.url.scheme}://{request.url.netloc}"
            mcp_endpoint = f"{base_url}/gradio_api/mcp"
            config = {"mcpServers": {"gradio": {"url": mcp_endpoint}}}
            return mcp_endpoint, config

        demo.load(get_mcp_info, outputs=[mcp_url, mcp_config])

    if mcp_server:
        try:
            mcp_server_instance = create_mcp_server(toolset)
            _integrate_mcp_server(demo, mcp_server_instance)
        except ImportError:
            pass

    demo.launch(css=css, footer_links=["settings"])


def _integrate_mcp_server(demo: gr.Blocks, mcp_server: "Server") -> None:
    """
    Integrate the MCP server with the Gradio demo.

    Args:
        demo: The Gradio Blocks instance.
        mcp_server: The MCP server instance to integrate.
    """
    if StreamableHTTPSessionManager is None:
        return

    manager = StreamableHTTPSessionManager(
        app=mcp_server, json_response=False, stateless=True
    )

    async def handle_streamable_http(
        scope: Scope, receive: Receive, send: Send
    ) -> None:
        path = scope.get("path", "")
        if not path.endswith(
            (
                "/gradio_api/mcp",
                "/gradio_api/mcp/",
                "/gradio_api/mcp/http",
                "/gradio_api/mcp/http/",
            )
        ):
            response = Response(
                content=f"Path '{path}' not found. The MCP HTTP transport is available at /gradio_api/mcp.",
                status_code=404,
            )
            await response(scope, receive, send)
            return

        await manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def mcp_lifespan(app: Starlette) -> AsyncIterator[None]:
        async with manager.run():
            try:
                yield
            finally:
                pass

    mcp_app = Starlette(
        routes=[
            Mount("/", app=handle_streamable_http),
        ],
    )

    original_create_app = gr.routes.App.create_app

    def create_app_wrapper(*args, **kwargs):
        app_kwargs = kwargs.get("app_kwargs") or {}
        user_lifespan = app_kwargs.get("lifespan")

        @contextlib.asynccontextmanager
        async def combined_lifespan(app: Starlette):
            async with contextlib.AsyncExitStack() as stack:
                await stack.enter_async_context(mcp_lifespan(app))
                if user_lifespan is not None:
                    await stack.enter_async_context(user_lifespan(app))
                yield

        app_kwargs["lifespan"] = combined_lifespan
        kwargs["app_kwargs"] = app_kwargs
        app = original_create_app(*args, **kwargs)
        app.mount("/gradio_api/mcp", mcp_app)
        return app

    gr.routes.App.create_app = create_app_wrapper
