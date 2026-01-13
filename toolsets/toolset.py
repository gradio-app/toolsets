from typing import Any, Dict, List, Optional

import gradio as gr

from .toolset_element import ToolsetElement


class Toolset:
    def __init__(self, name: Optional[str] = None):
        self._elements: List[ToolsetElement] = []
        self._tool_data: Dict[str, Dict[str, Any]] = {}
        self._name = name

    def add(self, element: ToolsetElement) -> "Toolset":
        self._elements.append(element)
        return self

    def _get_tool_data(self) -> Dict[str, Dict[str, Any]]:
        if self._tool_data:
            return
        for element in self._elements:
            tools = element.get_tools()
            for tool in tools:
                self._tool_data[tool.pop("name")] = tool

    def launch(self):
        self._get_tool_data()

        css = ".tool-item { cursor: pointer; }"
        
        with gr.Blocks() as demo:
            header_html = "<div style='display: flex; justify-content: space-between; align-items: center;'>"
            if self._name:
                header_html += f"<h1 style='margin: 0;'>{self._name}</h1>"
            header_html += "<img src='https://raw.githubusercontent.com/abidlabs/toolsets/main/logo.png' style='height: 3.5em; margin-left: auto; width: auto;'>"
            header_html += "</div>"
            gr.HTML(header_html)
            j = gr.JSON(label="inputSchema", value={}, render=False)

            with gr.Tab(f"Base tools ({len(self._tool_data)})"):
                with gr.Row():
                    with gr.Column():
                        for tool_name, tool_data in self._tool_data.items():
                            h = gr.HTML(f"<p><code>{tool_name}</code></p><p>{tool_data['description']}</p>", container=True, elem_classes="tool-item")
                            def make_click_handler(schema):
                                return lambda: schema
                            h.click(make_click_handler(tool_data["inputSchema"]), outputs=j)
                    with gr.Column():
                        j.render()
                        
            with gr.Tab(f"Tool search (disabled)"):
                    gr.Markdown("The `tool_search` tool is only enabled if you add a tool with `defer_loading=True`.")

        demo.launch(css=css, footer_links=["settings"])
