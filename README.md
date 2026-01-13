<div align="center">
  <img src="logo.png" alt="Toolsets Logo" width="60%">
</div>

# toolsets

A Python library for aggregating multiple MCP (Model Context Protocol) servers into a single unified MCP server. Toolsets acts as a pass-through server that combines tools from multiple sources and provides semantic search capabilities for deferred tool loading.

## Features

- **MCP Server Aggregation**: Combine tools from multiple Gradio Spaces and MCP servers and expose all aggregated tools through a single MCP endpoint
- **Gradio Interface**: Built-in UI for testing and exploring available tools
- **Deferred Tool Loading**: Use semantic search to discover and load tools on-demand



## Installation

```bash
pip install toolsets
```

For deferred tool loading with semantic search:

```bash
pip install toolsets[deferred]
```

## Quick Start

```python
from toolsets import Server, Toolset

# Create a toolset
t = Toolset("My Tools")

# Add tools from MCP servers
t.add(Server("gradio/mcp_tools"))
t.add(Server("username/space-name"))

# Launch the interface and MCP server
t.launch()
```

## Examples

### Basic Usage

```python
from toolsets import Server, Toolset

t = Toolset("Podcasting Tools")

# Add tools from a Gradio Space
t.add(Server("gradio/mcp_tools"))

# Launch interface at http://localhost:7860
# MCP server available at http://localhost:7860/gradio_api/mcp
t.launch()
```

### Deferred Tool Loading

```python
from toolsets import Server, Toolset

t = Toolset("My Tools")

# Add tools with deferred loading (enables semantic search)
t.add(Server("gradio/mcp_tools"), defer_loading=True)

# Regular tools are immediately available
t.add(Server("gradio/mcp_letter_counter_app"))

t.launch()
```

When tools are added with `defer_loading=True`:
- Tools are not exposed in the base tools list
- Two special MCP tools are added: "Search Deferred Tools" and "Call Deferred Tool"
- A search interface is available in the Gradio UI for finding deferred tools
- Tools can be discovered using semantic search based on natural language queries

### Custom Embedding Model

```python
from toolsets import Toolset

# Use a different sentence-transformers model
t = Toolset("My Tools", embedding_model="all-mpnet-base-v2")
t.add(Server("gradio/mcp_tools"), defer_loading=True)
t.launch()
```

## Roadmap

Upcoming features and improvements:

- [ ] **More Complete Examples**: Comprehensive examples demonstrating advanced use cases, integration patterns, and best practices
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
