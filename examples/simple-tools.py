from toolsets import Server, Toolset

t = Toolset("Simple Tools")

t.add(Server("gradio/mcp_tools"))
t.add(Server("gradio/mcp_letter_counter_app"))

t.launch()
