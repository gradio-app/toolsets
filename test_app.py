from toolsets import Toolset

if __name__ == "__main__":
    toolset = Toolset()

    print("Adding tools from Gradio Spaces...")

    spaces = [
        "ResembleAI/chatterbox-turbo-demo",
        "fffiloni/diffusers-image-outpaint",
        "linoyts/Qwen-Image-Edit-Angles"
    ]

    for space in spaces:
        try:
            print(f"Adding tools from {space}...")
            toolset.add(space)
            print(f"✓ Successfully added tools from {space}")
        except Exception as e:
            print(f"✗ Failed to add tools from {space}: {e}")

    print("\nLaunching Gradio app...")
    print("The app will be available at http://localhost:7860")
    print("MCP server endpoint will be available for testing\n")

    toolset.launch(port=7860, share=False)

