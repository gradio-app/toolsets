from toolsets import Server, Toolset

t = Toolset()

t.add(Server("prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast"))
t.add(Server("zerogpu-aoti/wan2-2-fp8da-aoti"))
t.add(Server("https://linoyts-qwen-image-edit-angles.hf.space/gradio_api/mcp/"))

t.launch()
