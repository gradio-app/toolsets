from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ToolsetElement(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Any:
        pass
