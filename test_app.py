from toolsets import Toolset, Server

t = Toolset()

t.add(
    Server(
        "ResembleAI/chatterbox-turbo-d  emo",
        tools=["generate_speech", "list_voices"]
    )
).add(
    Server(
        "fffiloni/diffusers-image-outpaint",
        tools=["outpaint"]
    )
)

t.launch()