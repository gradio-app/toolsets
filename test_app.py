from toolsets import Server, Toolset

t = Toolset("Podcasting Tools")

t.add(Server("gradio/mcp_tools"))

t.launch()
