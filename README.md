<div align="center">
  <img src="logo.png" alt="Toolsets Logo" width="60%">
</div>

# toolsets

A Python library for aggregating multiple MCP (Model Context Protocol) servers into a single unified MCP server. Toolsets acts as a pass-through server that combines tools from multiple sources and provides semantic search capabilities for deferred tool loading.

## Features

- **MCP Server Aggregation**: Combine tools from multiple Gradio Spaces and MCP servers
- **Pass-Through MCP Server**: Expose all aggregated tools through a single MCP endpoint
- **Deferred Tool Loading**: Use semantic search to discover and load tools on-demand
- **Gradio Interface**: Built-in UI for testing and exploring available tools

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

## API Reference

### `Toolset(name: Optional[str] = None, embedding_model: Optional[str] = None)`

Create a new Toolset instance.

**Parameters:**
- `name` (Optional[str]): Name for the toolset (displayed in UI)
- `embedding_model` (Optional[str]): Sentence-transformers model name for deferred tools (default: "all-MiniLM-L6-v2")

### `add(element: ToolsetElement, defer_loading: bool = False) -> Toolset`

Add a toolset element (e.g., Server) to the toolset.

**Parameters:**
- `element` (ToolsetElement): The toolset element to add (typically a `Server` instance)
- `defer_loading` (bool): If True, tools are deferred and accessible via semantic search

**Returns:**
- `Toolset`: Returns self for method chaining

### `launch()`

Launch the Gradio interface and MCP server. The MCP server is available at `/gradio_api/mcp`.

### `create_mcp_server() -> Server`

Create an MCP server instance that can be integrated into custom applications.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License
