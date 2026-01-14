<div align="center">
  <img src="logo.png" alt="Toolsets Logo" width="60%">
</div>

# `toolsets`

A Python library for aggregating multiple MCP (Model Context Protocol) servers into a single unified MCP server. Toolsets acts as a pass-through server that combines tools from multiple sources and provides semantic search capabilities for deferred tool loading.

## Features

- **MCP Server Aggregation**: Combine tools from multiple Gradio Spaces and MCP servers and expose all aggregated tools through a single MCP endpoint (optional, enabled with `mcp_server=True`).
- **Free hosting on Hugging Face Spaces**: A Toolset itself is _also_ a Gradio application (including a built-in UI for testing and exploring available tools), so you can host it for free on [Hugging Face Spaces](https://huggingface.co/spaces/)
- **Deferred Tool Loading**: Use semantic search to discover and load tools on-demand. Like Claude's [Advanced Tool Usage](https://www.anthropic.com/engineering/advanced-tool-use) but for any LLM. This is useful when you have 100s of tools or more as it can save the context length of your model.

<div align="center">
  <img width="80%" src="https://github.com/user-attachments/assets/851d1e5b-66d7-4000-ac98-2755b31b36ef" />
</div>

## Example Toolset

Check out a live example: https://huggingface.co/spaces/abidlabs/podcasting-toolset

<a href="https://huggingface.co/spaces/abidlabs/podcasting-toolset"><img width="1444" height="714" alt="image" src="https://github.com/user-attachments/assets/32e247f0-9e53-4d66-bebf-c106dd364da8" /></a>


## Create Your Own Toolset

### Installation

```bash
pip install toolsets
```

For deferred tool loading with semantic search:

```bash
pip install toolsets[deferred]
```

### Examples

A 

```python
from toolsets import Server, Toolset

# Create a toolset
t = Toolset("My Tools")

# Add tools from MCP servers on Spaces or arbitrary URLs 
t.add(Server("gradio/mcp_tools"))
t.add(Server("username/space-name"))

# Launch UI at http://localhost:7860
# MCP server available at http://localhost:7860/gradio_api/mcp (when mcp_server=True)
t.launch(mcp_server=True)
```

Deferred Tool Loading

```python
from toolsets import Server, Toolset

t = Toolset("My Tools")

# Add tools with deferred loading (enables semantic search)
t.add(Server("gradio/mcp_tools"), defer_loading=True)

# Regular tools are immediately available
t.add(Server("gradio/mcp_letter_counter_app"))

# Launch with MCP server enabled
t.launch(mcp_server=True)
```

When tools are added with `defer_loading=True`:
- Tools are not exposed in the base tools list
- Two special MCP tools are added: "Search Deferred Tools" and "Call Deferred Tool"
- A search interface is available in the Gradio UI for finding deferred tools
- Tools can be discovered using semantic search based on natural language queries

### MCP Server Configuration

By default, `launch()` only starts the Gradio UI without the MCP server. To enable the MCP server endpoint, pass `mcp_server=True`:

```python
from toolsets import Server, Toolset

t = Toolset("My Tools")
t.add(Server("gradio/mcp_tools"))

# Launch UI only (no MCP server)
t.launch()

# Launch UI with MCP server at http://localhost:7860/gradio_api/mcp
t.launch(mcp_server=True)
```

When `mcp_server=True`, the MCP server is available at `/gradio_api/mcp` and a configuration tab is shown in the UI with the connection details.

### Custom Embedding Model

```python
from toolsets import Server, Toolset

# Use a different sentence-transformers model
t = Toolset("My Tools", embedding_model="all-mpnet-base-v2")
t.add(Server("gradio/mcp_tools"), defer_loading=True)
t.launch(mcp_server=True)
```

### Guiding Tool Selection with Notes

When you have multiple tools that serve similar purposes, you can add `notes` to guide the LLM on when to use each tool. Notes are appended to the tool description and help the model make better decisions about which tool to call.

```python
from toolsets import Server, Toolset

t = Toolset("Podcasting Pro Tools")

t.add(Server("MohamedRashad/Audio-Separator"))
t.add(Server("hf-audio/whisper-large-v3", tools=["whisper_large_v3_transcribe"]))
t.add(Server("maya-research/maya1"), notes="Use this to generate voice samples, but not for the actual TTS since voice quality is lower.")
t.add(Server("ResembleAI/Chatterbox"), notes="Use this to generate the actual TTS, either without a voice sample or with a voice sample created with Maya1.")
t.add(Server("sanchit-gandhi/musicgen-streaming"))

t.launch(mcp_server=True)
```

In this example, both Maya1 and Chatterbox can generate speech, but the notes clarify their intended use:
- Maya1 is best for creating voice samples (reference audio)
- Chatterbox should be used for final TTS output, optionally using Maya1's output as a voice sample

The tool description format can be customized using the `tool_description_format` parameter:

```python
# Default format includes the note
t = Toolset("My Tools")  # "[{toolset_name} Toolset] {tool_description} {note}"

# Custom format
t = Toolset("My Tools", tool_description_format="({toolset_name}) {tool_description} | Note: {note}")

# Disable formatting entirely
t = Toolset("My Tools", tool_description_format=False)
```

### Deploying to Hugging Face Spaces

To deploy your toolset to Hugging Face Spaces:

1. Go to [https://huggingface.co/new-space](https://huggingface.co/new-space)
2. Select the **Gradio** SDK
3. Create your toolset file (e.g., `app.py`) with your toolset code
4. Add a `requirements.txt` file with `toolsets` (and optionally `toolsets[deferred]` for semantic search)

Your toolset will be available as both a Gradio UI and an MCP server endpoint.

## Roadmap

Upcoming features and improvements:

- [ ] **Hugging Face Token Support**: Automatic token passing in headers for private and ZeroGPU spaces
- [ ] **Hugging Face Data Types Integration**:
  - [ ] **Datasets**: Add Hugging Face datasets for easy RAG on documentation and structured data
  - [ ] **Models**: Support for models with inference provider usage (e.g., Inference API, Inference Endpoints)
  - [ ] **Papers**: Search and query capabilities for Hugging Face Papers
- [ ] **Enhanced Error Handling**: Better retry logic, connection pooling, and graceful degradation
- [ ] **Tool Caching**: Cache tool definitions and embeddings to reduce API calls and improve startup time

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License
