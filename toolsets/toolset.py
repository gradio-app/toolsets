import contextlib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import gradio as gr
from anyio.to_thread import run_sync
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from .toolset_element import ToolsetElement

if TYPE_CHECKING:
    from mcp import types
    from mcp.server import Server
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
else:
    try:
        from mcp import types
        from mcp.server import Server
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    except ImportError:
        types = None
        Server = None
        StreamableHTTPSessionManager = None


class Toolset:
    def __init__(self, name: Optional[str] = None):
        self._elements: List[ToolsetElement] = []
        self._tool_data: Dict[str, Dict[str, Any]] = {}
        self._tool_to_element: Dict[str, ToolsetElement] = {}
        self._name = name

    def add(self, element: ToolsetElement) -> "Toolset":
        self._elements.append(element)
        return self

    def _get_tool_data(self) -> Dict[str, Dict[str, Any]]:
        if self._tool_data:
            return self._tool_data
        for element in self._elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                self._tool_data[tool_name] = tool
                self._tool_to_element[tool_name] = element
        return self._tool_data

    def launch(self):
        self._get_tool_data()

        css = ".tool-item { cursor: pointer; }"

        with gr.Blocks() as demo:
            header_html = "<div style='display: flex; justify-content: space-between; align-items: center;'>"
            if self._name:
                header_html += f"<h1 style='margin: 0;'>{self._name}</h1>"
            header_html += "<img src='https://raw.githubusercontent.com/abidlabs/toolsets/main/logo.png' style='height: 3.5em; margin-left: auto; width: auto;'>"
            header_html += "</div>"
            gr.HTML(header_html)
            j = gr.JSON(label="inputSchema", value={}, render=False)

            with gr.Tab(f"Base tools ({len(self._tool_data)})"):
                with gr.Row():
                    with gr.Column():
                        for tool_name, tool_data in self._tool_data.items():
                            h = gr.HTML(
                                f"<p><code>{tool_name}</code></p><p>{tool_data['description']}</p>",
                                container=True,
                                elem_classes="tool-item",
                            )

                            def make_click_handler(schema):
                                return lambda: schema

                            h.click(
                                make_click_handler(tool_data["inputSchema"]), outputs=j
                            )
                    with gr.Column():
                        j.render()

            with gr.Tab(f"Tool search (disabled)"):
                gr.Markdown(
                    "The `tool_search` tool is only enabled if you add a tool with `defer_loading=True`."
                )

            with gr.Tab("MCP Info"):
                gr.Markdown(
                    "This MCP server was created with the [toolsets](https://github.com/abidlabs/toolsets) library."
                )
                mcp_url = gr.Markdown()

            def get_mcp_url(request: gr.Request):
                base_url = f"{request.url.scheme}://{request.url.netloc}"
                return f"MCP Server running using Streamable HTTP: {base_url}/gradio_api/mcp"

            demo.load(get_mcp_url, outputs=mcp_url)

        try:
            mcp_server = self.create_mcp_server()
            self._integrate_mcp_server(demo, mcp_server)
        except ImportError:
            pass

        demo.launch(css=css, footer_links=["settings"])

    def _integrate_mcp_server(self, demo: gr.Blocks, mcp_server: "Server") -> None:
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

    def create_mcp_server(self) -> "Server":
        """
        Create an MCP server that acts as a pass-through for all tools in this toolset.

        Returns:
            The MCP server instance.
        """
        if Server is None:
            raise ImportError(
                "The `mcp` package is required to create an MCP server. "
                "Please install it with: `pip install gradio[mcp]`"
            )

        self._get_tool_data()
        server = Server(str(self._name or "Toolset"))

        @server.list_tools()
        async def list_tools() -> list[types.Tool]:
            tools = []
            for tool_name, tool_data in self._tool_data.items():
                tools.append(
                    types.Tool(
                        name=tool_name,
                        description=tool_data.get("description", ""),
                        inputSchema=tool_data.get("inputSchema", {}),
                    )
                )
            return tools

        @server.call_tool()
        async def call_tool(
            name: str, arguments: dict[str, Any]
        ) -> types.CallToolResult:
            if name not in self._tool_to_element:
                raise ValueError(f"Tool '{name}' not found")

            element = self._tool_to_element[name]
            result = await run_sync(lambda: element.execute_tool(name, arguments))

            if result is None:
                content = []
            else:
                content = [types.TextContent(type="text", text=str(result))]

            return types.CallToolResult(content=content)

        return server
