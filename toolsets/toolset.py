from typing import Any

import numpy as np

from .gradio_ui import launch_gradio_ui
from .toolset_element import ToolsetElement


class Toolset:
    """
    A toolset that aggregates tools from multiple MCP servers and provides a unified interface.

    Toolsets can combine tools from multiple sources (Gradio Spaces, MCP servers) and expose them
    through a single Gradio UI and optional MCP server endpoint. Supports deferred tool loading with
    semantic search for efficient discovery of tools when dealing with large numbers of tools.

    Examples:
        Basic usage:
        >>> from toolsets import Server, Toolset
        >>> t = Toolset("My Tools")
        >>> t.add(Server("gradio/mcp_tools"))
        >>> t.launch(mcp_server=True)

        With deferred loading:
        >>> t = Toolset("My Tools")
        >>> t.add(Server("gradio/mcp_tools"), defer_loading=True)
        >>> t.launch(mcp_server=True)
    """

    def __init__(
        self,
        name: str | None = None,
        embedding_model: str | None = None,
        verbose: bool = True,
        tool_description_format: str
        | bool
        | None = "[{toolset_name} Toolset] {tool_description}",
    ):
        """
        Initialize a Toolset.

        Args:
            name: The name of the toolset. Used in the UI and for prepending to tool descriptions.
                If None, defaults to "Toolset" in some contexts.
            embedding_model: The sentence-transformers model name to use for semantic search of
                deferred tools. Defaults to "all-MiniLM-L6-v2". Only used when tools are added
                with defer_loading=True.
            verbose: If True, print messages when tools are added. Defaults to True.
            tool_description_format: Format string for prepending toolset name to tool descriptions.
                Uses placeholders: {toolset_name} for the toolset name and {tool_description} for
                the original description. Defaults to "[{toolset_name} Toolset] {tool_description}".
                Set to False, None, or "" to disable prepending.

        Examples:
            >>> t = Toolset("My Tools")
            >>> t = Toolset("My Tools", embedding_model="all-mpnet-base-v2")
            >>> t = Toolset("My Tools", tool_description_format="{toolset_name}: {tool_description}")
            >>> t = Toolset("My Tools", tool_description_format=False)  # Disable prepending
        """
        self._elements: list[ToolsetElement] = []
        self._deferred_elements: list[ToolsetElement] = []
        self._tool_data: dict[str, dict[str, Any]] = {}
        self._tool_to_element: dict[str, ToolsetElement] = {}
        self._deferred_tool_data: dict[str, dict[str, Any]] = {}
        self._deferred_tool_to_element: dict[str, ToolsetElement] = {}
        self._deferred_tool_embeddings: list[list[float]] | None = None
        self._deferred_tool_names: list[str] = []
        self._embedding_model_name = embedding_model or "all-MiniLM-L6-v2"
        self._name = name
        self._verbose = verbose
        self._tool_description_format = (
            None if tool_description_format is False else tool_description_format
        )

    def add(self, element: ToolsetElement, defer_loading: bool = False) -> "Toolset":
        """
        Add a toolset element (e.g., an MCP server) to this toolset.

        Args:
            element: The toolset element to add (typically a Server instance).
            defer_loading: If True, tools from this element are not immediately loaded.
                Instead, they can be discovered via semantic search using the "Search Deferred Tools"
                tool. This is useful when dealing with large numbers of tools to save context length.
                Defaults to False.

        Returns:
            Self for method chaining.

        Examples:
            >>> from toolsets import Server, Toolset
            >>> t = Toolset("My Tools")
            >>> t.add(Server("gradio/mcp_tools"))
            >>> t.add(Server("gradio/mcp_letter_counter_app"), defer_loading=True)
        """
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

    def _get_tool_data(self) -> dict[str, dict[str, Any]]:
        if self._tool_data:
            return self._tool_data
        for element in self._elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                tool_copy = tool.copy()
                if self._tool_description_format and self._name:
                    description = tool_copy.get("description", "")
                    if description:
                        tool_copy["description"] = self._tool_description_format.format(
                            toolset_name=self._name, tool_description=description
                        )
                self._tool_data[tool_name] = tool_copy
                self._tool_to_element[tool_name] = element
        return self._tool_data

    def _get_deferred_tool_data(self) -> dict[str, dict[str, Any]]:
        if self._deferred_tool_data:
            return self._deferred_tool_data
        for element in self._deferred_elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                tool_copy = tool.copy()
                if self._tool_description_format and self._name:
                    description = tool_copy.get("description", "")
                    if description:
                        tool_copy["description"] = self._tool_description_format.format(
                            toolset_name=self._name, tool_description=description
                        )
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
    ) -> list[dict[str, Any]]:
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

    def launch(self, mcp_server: bool = False):
        """
        Launch the Gradio UI for this toolset.

        Starts a Gradio web interface that displays all available tools, allows testing them,
        and optionally exposes an MCP server endpoint for programmatic access.

        Args:
            mcp_server: If True, creates and integrates an MCP server that exposes all tools
                through the MCP protocol at the `/gradio_api/mcp` endpoint. The MCP server
                can be accessed by MCP clients for programmatic tool usage. Defaults to False.

        Examples:
            >>> from toolsets import Server, Toolset
            >>> t = Toolset("My Tools")
            >>> t.add(Server("gradio/mcp_tools"))
            >>> t.launch()  # UI only
            >>> t.launch(mcp_server=True)  # UI + MCP server

        Note:
            When mcp_server=True, the MCP server endpoint is available at
            `http://localhost:7860/gradio_api/mcp` (or the appropriate host/port).
            Connection details are shown in the "MCP Info" tab of the UI.
        """
        launch_gradio_ui(self, mcp_server=mcp_server)
