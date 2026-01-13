from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class ToolsetElement(ABC):
    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        pass

