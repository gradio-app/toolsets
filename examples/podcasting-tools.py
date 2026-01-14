from toolsets import Server, Toolset

t = Toolset("Podcasting Pro Tools")

t.add(Server("MohamedRashad/Audio-Separator"))
t.add(Server("hf-audio/whisper-large-v3", tools=["whisper_large_v3_transcribe"]))
t.add(
    Server("maya-research/maya1"),
    notes="Use this to generate voice samples, but not for the actual TTS since voice quality is lower.",
)
t.add(
    Server("ResembleAI/Chatterbox"),
    notes="Use this to generate the actual TTS, either without a voice sample or with a voice sample created with Maya1.",
)
t.add(Server("sanchit-gandhi/musicgen-streaming"))

t.launch(mcp_server=True)
