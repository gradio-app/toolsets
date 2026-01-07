from typing import List, Optional, Dict, Any
from sentence_transformers import SentenceTransformer
import os

from .vector_store import VectorStore
from .mcp_client import MCPClient


class Toolset:
    def __init__(self, persist_directory: Optional[str] = None):
        self.vector_store = VectorStore(persist_directory)
        self.embedder = None
        self._spaces: Dict[str, str] = {}
        self._tool_registry: Dict[str, Dict[str, Any]] = {}

    def _get_embedder(self) -> SentenceTransformer:
        if self.embedder is None:
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self.embedder

    def add(
        self,
        url_or_space: str,
        tools: Optional[List[str]] = None
    ):
        """
        Add tools from a Gradio Space or a full URL pointing to the /mcp
        """
        embedder = self._get_embedder()
        client = MCPClient("")

        try:
            normalized_url = client._normalize_space_url(space_name_or_url)
            if "/" in space_name_or_url:
                space_name = space_name_or_url.split("/")[-1]
            else:
                space_name = space_name_or_url

            mcp_tools = client.get_tools(space_name_or_url)

            if tools is not None:
                tool_names_set = set(tools)
                mcp_tools = [t for t in mcp_tools if t.get("name") in tool_names_set]

            for tool in mcp_tools:
                tool_name = tool.get("name", "unknown")
                tool_id = f"{space_name}::{tool_name}"
                description = tool.get("description", "")
                schema = tool.get("inputSchema", {})

                text_to_embed = f"{tool_name}: {description}"
                embedding = embedder.encode(text_to_embed).tolist()

                self.vector_store.add_tool(
                    tool_id=tool_id,
                    name=tool_name,
                    description=description,
                    schema=schema,
                    space_url=normalized_url,
                    space_name=space_name,
                    embedding=embedding
                )

                self._tool_registry[tool_id] = {
                    "space_url": normalized_url,
                    "space_name": space_name,
                    "tool_name": tool_name
                }

            self._spaces[space_name] = normalized_url

        finally:
            client.close()

    def search_tools(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        embedder = self._get_embedder()
        query_embedding = embedder.encode(query).tolist()
        return self.vector_store.search(query_embedding, top_k=k)

    def execute_tool(self, tool_id: str, parameters: Dict[str, Any]) -> Any:
        if tool_id not in self._tool_registry:
            raise ValueError(f"Tool {tool_id} not found in registry")

        tool_info = self._tool_registry[tool_id]
        space_url = tool_info["space_url"]
        tool_name = tool_info["tool_name"]

        client = MCPClient("")
        try:
            return client.execute_tool(tool_name, parameters, space_url)
        finally:
            client.close()

    def launch(self, port: int = 7860, share: bool = False, server_name: Optional[str] = None):
        from .gradio_app import create_gradio_app
        app = create_gradio_app(self)
        app.launch(
            server_name=server_name,
            server_port=port,
            share=share,
            mcp_server=True
        )

