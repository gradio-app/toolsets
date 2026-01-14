from toolsets import Server, Toolset

t = Toolset("Podcasting Pro Tools")

t.add(Server("MohamedRashad/Audio-Separator"))
t.add(Server("hf-audio/whisper-large-v3", tools=["whisper_large_v3_transcribe"]))
t.add(Server("ResembleAI/Chatterbox"))
t.add(Server("maya-research/maya1"))
t.add(Server("sanchit-gandhi/musicgen-streaming"))

t.launch(mcp_server=True)
