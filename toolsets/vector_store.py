import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import os
import json


class VectorStore:
    def __init__(self, persist_directory: Optional[str] = None):
        if persist_directory is None:
            persist_directory = os.path.join(os.path.expanduser("~"), ".toolsets", "chroma")
        os.makedirs(persist_directory, exist_ok=True)

        self.schemas_file = os.path.join(persist_directory, "tool_schemas.json")

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="tools",
            metadata={"hnsw:space": "cosine"}
        )

        self._load_schemas()

    def add_tool(
        self,
        tool_id: str,
        name: str,
        description: str,
        schema: Dict[str, Any],
        url: str,
        embedding: List[float]
    ):
        self.collection.add(
            ids=[tool_id],
            embeddings=[embedding],
            documents=[f"{name}: {description}"],
            metadatas=[{
                "name": name,
                "description": description,
                "url": url,
                "tool_id": tool_id
            }]
        )
        self._tool_schemas[tool_id] = schema
        self._save_schemas()

    def search(self, query_embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )

        tools = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i, tool_id in enumerate(results["ids"][0]):
                metadata = results["metadatas"][0][i]
                tool_schema = self.get_tool_schema(tool_id)
                tools.append({
                    "id": tool_id,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "url": metadata["url"],
                    "schema": tool_schema,
                    "distance": results["distances"][0][i] if results["distances"] else None
                })
        return tools

    def _load_schemas(self):
        if os.path.exists(self.schemas_file):
            try:
                with open(self.schemas_file, "r") as f:
                    self._tool_schemas = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._tool_schemas = {}
        else:
            self._tool_schemas = {}

    def _save_schemas(self):
        try:
            with open(self.schemas_file, "w") as f:
                json.dump(self._tool_schemas, f, indent=2)
        except IOError:
            pass

    def get_tool_schema(self, tool_id: str) -> Dict[str, Any]:
        return self._tool_schemas.get(tool_id, {})

    def get_all_tools(self) -> List[str]:
        return self.collection.get()["ids"]

    def clear(self):
        self.client.delete_collection(name="tools")
        self.collection = self.client.get_or_create_collection(
            name="tools",
            metadata={"hnsw:space": "cosine"}
        )
        self._tool_schemas = {}
        if os.path.exists(self.schemas_file):
            os.remove(self.schemas_file)

