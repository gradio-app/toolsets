from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ToolsetElement(ABC):
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        pass
