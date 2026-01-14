from typing import Any, Dict, List, Optional

import numpy as np

from .gradio_ui import launch_gradio_ui
from .toolset_element import ToolsetElement


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

    def launch(self, mcp_server: bool = False):
        launch_gradio_ui(self, mcp_server=mcp_server)
