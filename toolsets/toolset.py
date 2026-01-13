from typing import List, Optional
from .toolset_element import ToolsetElement


class Toolset:
    def __init__(self):
        self._elements: List[ToolsetElement] = []

    def add(self, element: ToolsetElement) -> "Toolset":
        self._elements.append(element)
        return self

    def launch(self, port: int = 7860, share: bool = False, server_name: Optional[str] = None):
        pass
