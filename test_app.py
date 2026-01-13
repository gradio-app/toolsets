from toolsets import Server, Toolset

t = Toolset()

t.add(Server("gradio/mcp_tools"))

t.launch()
