<div align="center">
  <img src="logo.png" alt="Toolsets Logo" width="60%">
</div>

# `toolsets`

A Python library for aggregating multiple MCP (Model Context Protocol) servers into a single unified MCP server. Toolsets acts as a pass-through server that combines tools from multiple sources and provides semantic search capabilities for deferred tool loading.

## Features

- **MCP Server Aggregation**: Combine tools from multiple Gradio Spaces and MCP servers and expose all aggregated tools through a single MCP endpoint (optional, enabled with `mcp_server=True`).
- **Free hosting on Hugging Face Spaces**: A Toolset itself is _also_ a Gradio application (including a built-in UI for testing and exploring available tools), so you can host it for free on [Hugging Face Spaces](https://huggingface.co/spaces/)
- **Deferred Tool Loading**: Use semantic search to discover and load tools on-demand. Like Claude's [Advanced Tool Usage](https://www.anthropic.com/engineering/advanced-tool-use) but for any LLM. This is useful when you have 100s of tools or more as it can save the context length of your model.

<img width="1408" height="768" alt="Gemini_Generated_Image_7za89y7za89y7za8_50 (1)" src="https://github.com/user-attachments/assets/851d1e5b-66d7-4000-ac98-2755b31b36ef" />

## Example Toolset

* 

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
from toolsets import Toolset

# Use a different sentence-transformers model
t = Toolset("My Tools", embedding_model="all-mpnet-base-v2")
t.add(Server("gradio/mcp_tools"), defer_loading=True)
t.launch(mcp_server=True)
```

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
