from typing import List

import gradio as gr

from .toolset_element import ToolsetElement


class Toolset:
    def __init__(self):
        self._elements: List[ToolsetElement] = []
        self._tool_data: Dict[str, Dict[str, Any]] = None

    def add(self, element: ToolsetElement) -> "Toolset":
        self._elements.append(element)
        return self

    def _get_tool_data(self) -> Dict[str, Dict[str, Any]]:
        if self._tool_data is not None:
            return
        for element in self._elements:
            tools = element.get_tools()
            for tool in tools:
                self._tool_data[tool.pop("name")] = tool

    def launch(self):
        self._get_tool_data()

        with gr.Blocks() as demo:
            gr.Markdown(f"This Toolset contains {len(self._tool_data)} tools:")
            for tool_name, tool_data in self._tool_data.items():
                gr.Markdown(f"### {tool_name}")
                gr.Markdown(f"**Description:** {tool_data['description']}")
                gr.Markdown(f"**Input Schema:** {tool_data['inputSchema']}")

        demo.launch()
