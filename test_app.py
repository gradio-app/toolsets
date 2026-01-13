from toolsets import Toolset, Server

t = Toolset()

t.add(
    Server(
        "prithivMLmods/Qwen-Image-Edit-2511-LoRAs-Fast"
    )
).add(
    Server(
        "zerogpu-aoti/wan2-2-fp8da-aoti"
    )
).add(
    Server(
        "https://linoyts-qwen-image-edit-angles.hf.space/gradio_api/mcp/"
    )
)

t.launch()
