from typing import List, Optional, Dict, Any, TYPE_CHECKING
import os

from .vector_store import VectorStore
from .mcp_client import get_mcp_tools, execute_tool, normalize_space_url

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class Toolset:
    def __init__(self, persist_directory: Optional[str] = None):
        self.vector_store = VectorStore(persist_directory)
        self.embedder = None
        self._urls: Dict[str, str] = {}
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self._pending_tools: List[Dict[str, Any]] = []

    def _get_embedder(self):
        if self.embedder is None:
            from sentence_transformers import SentenceTransformer
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self.embedder

    def add(
        self,
        url_or_space: str,
        tools: Optional[List[str]] = None,
        defer_loading: bool = False
    ):
        """
        Add tools from an existing MCP server to the toolset.

        Parameters:
            url_or_space: The full URL to the /mcp endpoint (e.g. https://username-spacename.hf.space/gradio_api/mcp) or Gradio Space name ("username/spacename") of the MCP server to add.
            tools: Optional list of tool names to filter. If None, all tools are added from the MCP server.
            defer_loading: If True, the MCP tool descriptions will not be loaded and instead the Toolset will use a "tool search" tool to find tools matching the user's query.
        """
        normalized_url = normalize_space_url(url_or_space)

        mcp_tools = get_mcp_tools(url_or_space)

        if tools is not None:
            tool_names_set = set(tools)
            mcp_tools = [t for t in mcp_tools if t.get("name") in tool_names_set]

        for tool in mcp_tools:
            tool_name = tool.get("name", "unknown")
            tool_id = f"{normalized_url}::{tool_name}"
            description = tool.get("description", "")
            schema = tool.get("inputSchema", {})

            self._tool_registry[tool_id] = {
                "url": normalized_url,
                "tool_name": tool_name,
                "description": description,
                "schema": schema
            }

            if defer_loading:
                embedder = self._get_embedder()
                text_to_embed = f"{tool_name}: {description}"
                embedding = embedder.encode(text_to_embed).tolist()

                self.vector_store.add_tool(
                    tool_id=tool_id,
                    name=tool_name,
                    description=description,
                    schema=schema,
                    url=normalized_url,
                    embedding=embedding
                )

        self._urls[normalized_url] = normalized_url

    def search_tools(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        embedder = self._get_embedder()
        query_embedding = embedder.encode(query).tolist()
        return self.vector_store.search(query_embedding, top_k=k)

    def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Any:
        if tool_id not in self._tool_registry:
            raise ValueError(f"Tool {tool_id} not found in registry")

        tool_info = self._tool_registry[tool_id]
        url = tool_info["url"]
        tool_name = tool_info["tool_name"]

        return execute_tool(url, tool_name, parameters)

    def launch(self, port: int = 7860, share: bool = False, server_name: Optional[str] = None):
        from .gradio_app import create_gradio_app
        app = create_gradio_app(self)
        app.launch(
            server_name=server_name,
            server_port=port,
            share=share,
            mcp_server=True
        )

