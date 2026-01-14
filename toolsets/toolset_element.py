from abc import ABC, abstractmethod
from typing import Any


class ToolsetElement(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_tools(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, parameters: dict[str, Any]) -> Any:
        pass
