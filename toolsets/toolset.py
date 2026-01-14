import contextlib
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import gradio as gr
from starlette.applications import Starlette
from starlette.responses import Response
from starlette.routing import Mount
from starlette.types import Receive, Scope, Send

from .mcp_server import create_mcp_server
from .toolset_element import ToolsetElement

if TYPE_CHECKING:
    from mcp.server import Server
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
else:
    try:
        from mcp.server import Server
        from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    except ImportError:
        Server = None
        StreamableHTTPSessionManager = None


class Toolset:
    def __init__(
        self,
        name: Optional[str] = None,
        embedding_model: Optional[str] = None,
        verbose: bool = True,
    ):
        self._elements: List[ToolsetElement] = []
        self._deferred_elements: List[ToolsetElement] = []
        self._tool_data: Dict[str, Dict[str, Any]] = {}
        self._tool_to_element: Dict[str, ToolsetElement] = {}
        self._deferred_tool_data: Dict[str, Dict[str, Any]] = {}
        self._deferred_tool_to_element: Dict[str, ToolsetElement] = {}
        self._deferred_tool_embeddings: Optional[List[List[float]]] = None
        self._deferred_tool_names: List[str] = []
        self._embedding_model_name = embedding_model or "all-MiniLM-L6-v2"
        self._name = name
        self._verbose = verbose

    def add(self, element: ToolsetElement, defer_loading: bool = False) -> "Toolset":
        if defer_loading:
            self._deferred_elements.append(element)
            self._tool_data = {}
            if self._verbose:
                print("* (Deferred) tools added from", element.name)
        else:
            self._elements.append(element)
            tools = element.get_tools()
            if self._verbose:
                print(
                    f"* ({len(tools)}) tools added from {element.name}: {[t['name'] for t in tools]}"
                )
        return self

    def _get_tool_data(self) -> Dict[str, Dict[str, Any]]:
        if self._tool_data:
            return self._tool_data
        for element in self._elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                tool_copy = tool.copy()
                self._tool_data[tool_name] = tool_copy
                self._tool_to_element[tool_name] = element
        return self._tool_data

    def _get_deferred_tool_data(self) -> Dict[str, Dict[str, Any]]:
        if self._deferred_tool_data:
            return self._deferred_tool_data
        for element in self._deferred_elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                tool_copy = tool.copy()
                self._deferred_tool_data[tool_name] = tool_copy
                self._deferred_tool_to_element[tool_name] = element
        return self._deferred_tool_data

    def _embed_deferred_tools(self) -> None:
        if self._deferred_tool_embeddings is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "The `sentence-transformers` package is required for deferred tools. "
                "Please install it with: `pip install toolsets[deferred]` or `pip install sentence-transformers`"
            ) from e

        self._get_deferred_tool_data()
        if not self._deferred_tool_data:
            return

        model = SentenceTransformer(self._embedding_model_name)

        texts = []
        self._deferred_tool_names = []
        for tool_name, tool_data in self._deferred_tool_data.items():
            description = tool_data.get("description", "")
            text = f"{tool_name} {description}".strip()
            texts.append(text)
            self._deferred_tool_names.append(tool_name)

        self._deferred_tool_embeddings = model.encode(
            texts, convert_to_numpy=True
        ).tolist()

    def _search_deferred_tools(
        self, query: str, top_k: int = 2
    ) -> List[Dict[str, Any]]:
        if not self._deferred_tool_data:
            return []

        try:
            self._embed_deferred_tools()
        except ImportError:
            return []

        if not self._deferred_tool_embeddings:
            return []

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            return []

        model = SentenceTransformer(self._embedding_model_name)
        query_embedding = model.encode([query], convert_to_numpy=True)[0]

        semantic_scores = []
        keyword_scores = []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        for i, tool_name in enumerate(self._deferred_tool_names):
            tool_data = self._deferred_tool_data[tool_name]
            tool_embedding = self._deferred_tool_embeddings[i]

            semantic_score = float(np.dot(query_embedding, tool_embedding))

            description = tool_data.get("description", "").lower()
            name_lower = tool_name.lower()
            keyword_matches = sum(
                1 for word in query_words if word in name_lower or word in description
            )
            keyword_score = keyword_matches / max(len(query_words), 1)

            semantic_scores.append(semantic_score)
            keyword_scores.append(keyword_score)

        semantic_scores = np.array(semantic_scores)
        keyword_scores = np.array(keyword_scores)

        semantic_normalized = (semantic_scores - semantic_scores.min()) / (
            semantic_scores.max() - semantic_scores.min() + 1e-8
        )
        keyword_normalized = keyword_scores

        final_scores = 0.7 * semantic_normalized + 0.3 * keyword_normalized

        top_indices = np.argsort(final_scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            tool_name = self._deferred_tool_names[idx]
            tool_data = self._deferred_tool_data[tool_name]
            results.append(
                {
                    "name": tool_name,
                    "description": tool_data.get("description", ""),
                    "inputSchema": tool_data.get("inputSchema", {}),
                }
            )

        return results

    def launch(self):
        self._get_tool_data()
        if self._verbose:
            message = f"\n* Launching Toolset UI and MCP server with ({len(self._tool_data)}) tools. "
            if self._deferred_elements:
                message += f"Additional deferred tools are available via tool search."
            print(message, "\n")
        if self._deferred_elements:
            try:
                self._embed_deferred_tools()
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
            if self._name:
                header_html += f"<h1 style='margin: 0;'>{self._name}</h1>"
            header_html += "<img src='https://raw.githubusercontent.com/abidlabs/toolsets/main/logo.png' style='height: 3.5em; margin-left: auto; width: auto;'>"
            header_html += "</div>"
            gr.HTML(header_html)
            j = gr.JSON(label="inputSchema", value={}, render=False)

            has_deferred = bool(self._deferred_elements)

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

                    def search_deferred(query: str):
                        if not query:
                            return []
                        results = self._search_deferred_tools(query, top_k=int(top_k))
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
                gr.Markdown(
                    "This MCP server was created with the [toolsets](https://github.com/abidlabs/toolsets) library."
                )
                mcp_url = gr.Markdown()

            def get_mcp_url(request: gr.Request):
                base_url = f"{request.url.scheme}://{request.url.netloc}"
                return f"MCP Server running using Streamable HTTP: {base_url}/gradio_api/mcp"

            demo.load(get_mcp_url, outputs=mcp_url)

        try:
            mcp_server = create_mcp_server(self)
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
