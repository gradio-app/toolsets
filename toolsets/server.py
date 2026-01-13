from typing import List, Optional, Dict, Any
from .toolset_element import ToolsetElement


class Server(ToolsetElement):
    def __init__(self, url_or_space: str, tools: Optional[List[str]] = None):
        self.url_or_space = url_or_space
        self.tools = tools

    def get_tools(self) -> List[Dict[str, Any]]:
        return []

