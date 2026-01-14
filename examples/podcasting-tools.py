from toolsets import Server, Toolset

t = Toolset("Podcasting Tools")

t.add(Server("MohamedRashad/Audio-Separator"))
# t.add(Server("Tonic/audiocraft"))
# t.add(Server("hf-audio/whisper-large-v3"))
# t.add(Server("ResembleAI/Chatterbox"))
# t.add(Server("maya-research/maya1"))

t.launch()
