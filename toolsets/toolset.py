from typing import Any

import numpy as np

from .gradio_ui import launch_gradio_ui
from .toolset_element import ToolsetElement

DEFAULT_EMBEDDING_MODEL = "ibm-granite/granite-embedding-small-english-r2"


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
        | None = "[{toolset_name} Toolset] {tool_description} {note}",
    ):
        """
        Initialize a Toolset.

        Args:
            name: The name of the toolset. Used in the UI and for prepending to tool descriptions.
                If None, defaults to "Toolset" in some contexts.
            embedding_model: The sentence-transformers model name to use for semantic search of
                deferred tools. Defaults to "ibm-granite/granite-embedding-small-english-r2".
                Only used when tools are added with defer_loading=True.
            verbose: If True, print messages when tools are added. Defaults to True.
            tool_description_format: Format string for tool descriptions.
                Uses placeholders: {toolset_name} for the toolset name, {tool_description} for
                the original description, and {note} for the note provided when adding the element.
                Defaults to "[{toolset_name} Toolset] {tool_description} {note}".
                Set to False, None, or "" to disable formatting.

        Examples:
            >>> t = Toolset("My Tools")
            >>> t = Toolset("My Tools", embedding_model="all-mpnet-base-v2")
            >>> t = Toolset("My Tools", tool_description_format="{toolset_name}: {tool_description}")
            >>> t = Toolset("My Tools", tool_description_format=False)  # Disable formatting
        """
        self._elements: list[tuple[ToolsetElement, str]] = []
        self._deferred_elements: list[tuple[ToolsetElement, str]] = []
        self._tool_data: dict[str, dict[str, Any]] = {}
        self._tool_to_element: dict[str, ToolsetElement] = {}
        self._deferred_tool_data: dict[str, dict[str, Any]] = {}
        self._deferred_tool_to_element: dict[str, ToolsetElement] = {}
        self._deferred_tool_embeddings: np.ndarray | None = None
        self._deferred_tool_names: list[str] = []
        self._embedding_model_name = embedding_model or DEFAULT_EMBEDDING_MODEL
        self._embedding_model: Any = None
        self._name = name
        self._verbose = verbose
        self._tool_description_format = (
            None if tool_description_format is False else tool_description_format
        )

    def add(
        self,
        element: ToolsetElement,
        defer_loading: bool = False,
        notes: str | None = None,
    ) -> "Toolset":
        """
        Add a toolset element (e.g., an MCP server) to this toolset.

        Args:
            element: The toolset element to add (typically a Server instance).
            defer_loading: If True, tools from this element are not immediately loaded.
                Instead, they can be discovered via semantic search using the "search_deferred_tools"
                tool. This is useful when dealing with large numbers of tools to save context length.
                Defaults to False.
            notes: Optional notes about when these tools should be used. This text is appended
                to each tool's description using the {note} placeholder in tool_description_format.
                Useful for guiding tool selection by the LLM.

        Returns:
            Self for method chaining.

        Examples:
            >>> from toolsets import Server, Toolset
            >>> t = Toolset("My Tools")
            >>> t.add(Server("gradio/mcp_tools"))
            >>> t.add(Server("gradio/mcp_letter_counter_app"), defer_loading=True)
            >>> t.add(Server("gradio/image_tools"), notes="Use these tools for image processing tasks.")
        """
        note = notes or ""
        if defer_loading:
            self._deferred_elements.append((element, note))
            self._tool_data = {}
            if self._verbose:
                print("* (Deferred) tools added from", element.name)
        else:
            self._elements.append((element, note))
            tools = element.get_tools()
            if self._verbose:
                print(
                    f"* ({len(tools)}) tools added from {element.name}: {[t['name'] for t in tools]}"
                )
        return self

    def _get_tool_data(self) -> dict[str, dict[str, Any]]:
        if self._tool_data:
            return self._tool_data
        for element, note in self._elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                tool_copy = tool.copy()
                if self._tool_description_format and self._name:
                    description = tool_copy.get("description", "")
                    if description:
                        tool_copy["description"] = self._tool_description_format.format(
                            toolset_name=self._name,
                            tool_description=description,
                            note=note,
                        ).strip()
                self._tool_data[tool_name] = tool_copy
                self._tool_to_element[tool_name] = element
        return self._tool_data

    def _get_deferred_tool_data(self) -> dict[str, dict[str, Any]]:
        if self._deferred_tool_data:
            return self._deferred_tool_data
        for element, note in self._deferred_elements:
            tools = element.get_tools()
            for tool in tools:
                tool_name = tool.pop("name")
                tool_copy = tool.copy()
                if self._tool_description_format and self._name:
                    description = tool_copy.get("description", "")
                    if description:
                        tool_copy["description"] = self._tool_description_format.format(
                            toolset_name=self._name,
                            tool_description=description,
                            note=note,
                        ).strip()
                self._deferred_tool_data[tool_name] = tool_copy
                self._deferred_tool_to_element[tool_name] = element
        return self._deferred_tool_data

    def _get_embedding_model(self) -> Any:
        if self._embedding_model is not None:
            return self._embedding_model

        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "The `sentence-transformers` package is required for deferred tools. "
                "Please install it with: `pip install toolsets[deferred]` or `pip install sentence-transformers`"
            ) from e

        model_kwargs = {}
        try:
            import torch

            if torch.cuda.is_available():
                model_kwargs["torch_dtype"] = "float16"
        except ImportError:
            pass

        self._embedding_model = SentenceTransformer(
            self._embedding_model_name,
            model_kwargs=model_kwargs if model_kwargs else None,
        )
        return self._embedding_model

    def _encode_documents(self, model: Any, texts: list[str]) -> np.ndarray:
        if hasattr(model, "encode_document"):
            embeddings = model.encode_document(texts, convert_to_numpy=True)
        else:
            embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    def _encode_query(self, model: Any, query: str) -> np.ndarray:
        if hasattr(model, "encode_query"):
            embedding = model.encode_query([query], convert_to_numpy=True)[0]
        else:
            embedding = model.encode([query], convert_to_numpy=True)[0]
        return embedding / np.linalg.norm(embedding)

    def _embed_deferred_tools(self) -> None:
        if self._deferred_tool_embeddings is not None:
            return

        self._get_deferred_tool_data()
        if not self._deferred_tool_data:
            return

        model = self._get_embedding_model()

        texts = []
        self._deferred_tool_names = []
        for tool_name, tool_data in self._deferred_tool_data.items():
            description = tool_data.get("description", "")
            text = f"{tool_name} {description}".strip()
            texts.append(text)
            self._deferred_tool_names.append(tool_name)

        self._deferred_tool_embeddings = self._encode_documents(model, texts)

    def _search_deferred_tools(
        self, query: str, top_k: int = 2
    ) -> list[dict[str, Any]]:
        if not self._deferred_tool_data:
            return []

        try:
            self._embed_deferred_tools()
        except ImportError:
            return []

        if self._deferred_tool_embeddings is None:
            return []

        model = self._get_embedding_model()
        query_embedding = self._encode_query(model, query)

        semantic_scores = np.dot(self._deferred_tool_embeddings, query_embedding)

        keyword_scores = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for tool_name in self._deferred_tool_names:
            tool_data = self._deferred_tool_data[tool_name]
            description = tool_data.get("description", "").lower()
            name_lower = tool_name.lower()
            keyword_matches = sum(
                1 for word in query_words if word in name_lower or word in description
            )
            keyword_score = keyword_matches / max(len(query_words), 1)
            keyword_scores.append(keyword_score)

        keyword_scores = np.array(keyword_scores)

        semantic_min, semantic_max = semantic_scores.min(), semantic_scores.max()
        semantic_normalized = (semantic_scores - semantic_min) / (
            semantic_max - semantic_min + 1e-8
        )

        final_scores = 0.7 * semantic_normalized + 0.3 * keyword_scores

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
