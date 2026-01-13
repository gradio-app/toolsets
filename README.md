<div align="center">
  <img src="logo.png" alt="Toolsets Logo" width="300">
</div>

# toolsets

A high-level abstraction layer that aggregates multiple MCP (Model Context Protocol) servers and tools into a single, unified entry point. Toolsets uses semantic search over tool embeddings to dynamically retrieve only the most relevant tools for each query, reducing context window bloat and improving LLM reasoning efficiency.

## Features

- **Semantic Tool Discovery**: Uses vector embeddings to find relevant tools based on natural language queries
- **MCP Server Aggregation**: Combine tools from multiple Gradio Spaces and MCP servers
- **Persistent Storage**: ChromaDB-based vector store that persists tool embeddings and schemas
- **Gradio Interface**: Built-in testing and deployment interface with MCP server support
- **Lightweight**: Uses local embeddings (sentence-transformers) - no API costs

## Installation

This package requires [Python 3.10 or higher](https://www.python.org/downloads/). Install with `pip`:

```bash
pip install toolsets
```

or with `uv`:

```bash
uv pip install toolsets
```

## Quick Start

```python
from toolsets import Toolset

# Create a toolset instance
toolset = Toolset()

# Add tools from a Gradio Space (MCP server)
toolset.add("ResembleAI/chatterbox-turbo-demo")

# Search for relevant tools
results = toolset.search_tools("generate speech from text", k=3)
for tool in results:
    print(f"{tool['name']}: {tool['description']}")

# Execute a tool
result = toolset.execute_tool(
    "ResembleAI/chatterbox-turbo-demo::generate_speech",
    {"text": "Hello, world!", "voice": "default"}
)

# Launch interactive Gradio interface
toolset.launch()
```

## Core Concepts

### Toolset Class

The `Toolset` class is the main interface for managing and using aggregated MCP tools.

#### Adding Tools

```python
toolset = Toolset()

# Add all tools from a Gradio Space
toolset.add("username/space-name")

# Add specific tools only
toolset.add("username/space-name", tools=["tool1", "tool2"])

# Add from full URL
toolset.add("https://huggingface.co/spaces/username/space-name")
```

When you call `add()`, the library:
1. Connects to the MCP server and fetches tool definitions
2. Generates semantic embeddings for each tool's name and description
3. Stores embeddings and schemas in the local ChromaDB vector store

#### Searching Tools

```python
# Search for tools matching a query
tools = toolset.search_tools("edit images", k=5)

# Each result contains:
# - id: Unique tool identifier (space_name::tool_name)
# - name: Tool name
# - description: Tool description
# - schema: JSON schema for tool parameters
# - space_url: URL of the source MCP server
# - space_name: Name of the source space
# - distance: Similarity distance (lower is better)
```

#### Executing Tools

```python
# Execute a tool with parameters
result = toolset.execute_tool(
    tool_id="space_name::tool_name",
    parameters={"param1": "value1", "param2": "value2"}
)
```

#### Launching the Interface

```python
# Launch Gradio interface for testing
toolset.launch(port=7860, share=False)

# With sharing enabled (for temporary public URL)
toolset.launch(port=7860, share=True)
```

The Gradio interface provides:
- **Search Tools**: Test semantic search with natural language queries
- **Execute Tool**: Run tools with custom parameters
- **Get Tool Schema**: View tool parameter schemas
- **Info**: List all registered spaces

## API Reference

### `Toolset`

#### `__init__(persist_directory: Optional[str] = None)`

Create a new Toolset instance.

**Parameters:**
- `persist_directory` (Optional[str]): Directory for storing ChromaDB data. Defaults to `~/.toolsets/chroma`.

**Example:**
```python
toolset = Toolset()
toolset = Toolset(persist_directory="./my_tools")
```

#### `add(space_name_or_url: str, tools: Optional[List[str]] = None)`

Register tools from an MCP server (Gradio Space).

**Parameters:**
- `space_name_or_url` (str): Gradio Space name (e.g., `"username/space"`) or full URL
- `tools` (Optional[List[str]]): Optional list of tool names to filter. If None, all tools are added.

**Raises:**
- `ConnectionError`: If unable to connect to the MCP server
- `ValueError`: If the server doesn't expose MCP tools

**Example:**
```python
toolset.add("ResembleAI/chatterbox-turbo-demo")
toolset.add("fffiloni/diffusers-image-outpaint", tools=["outpaint"])
```

#### `search_tools(query: str, k: int = 5) -> List[Dict[str, Any]]`

Perform semantic search to find relevant tools.

**Parameters:**
- `query` (str): Natural language query describing the desired functionality
- `k` (int): Number of top results to return (default: 5)

**Returns:**
- `List[Dict[str, Any]]`: List of tool dictionaries with metadata

**Example:**
```python
tools = toolset.search_tools("convert text to speech", k=3)
```

#### `execute_tool(tool_id: str, parameters: Dict[str, Any]) -> Any`

Execute a tool via its MCP server.

**Parameters:**
- `tool_id` (str): Tool identifier in format `space_name::tool_name`
- `parameters` (Dict[str, Any]): Tool parameters as a dictionary

**Returns:**
- `Any`: Tool execution result

**Raises:**
- `ValueError`: If tool_id is not found in registry
- `RuntimeError`: If tool execution fails

**Example:**
```python
result = toolset.execute_tool(
    "chatterbox-turbo-demo::generate_speech",
    {"text": "Hello", "voice": "default"}
)
```

#### `launch(port: int = 7860, share: bool = False, server_name: Optional[str] = None)`

Launch the Gradio interface and MCP server.

**Parameters:**
- `port` (int): Port to run the server on (default: 7860)
- `share` (bool): Create a public Gradio share link (default: False)
- `server_name` (Optional[str]): Server hostname (default: None for localhost)

**Example:**
```python
toolset.launch(port=7860, share=False)
```

## Architecture

Toolsets implements a **Router-Executor** pattern:

1. **Router**: Performs semantic search to identify relevant tools based on user queries
2. **Executor**: Executes selected tools via their original MCP servers
3. **Vector Store**: Maintains embeddings of tool names/descriptions in ChromaDB
4. **Gradio Interface**: Provides testing interface and serves as MCP server itself

### Data Flow

```
User Query
    ↓
Toolset.search_tools()
    ↓
Semantic Embedding (sentence-transformers)
    ↓
ChromaDB Vector Search
    ↓
Top-K Tool Schemas
    ↓
LLM Context (dynamic injection)
    ↓
Tool Selection
    ↓
Toolset.execute_tool()
    ↓
MCP Client → Original MCP Server
    ↓
Tool Result
```

### Storage

- **Embeddings**: Stored in ChromaDB with cosine similarity search
- **Schemas**: Persisted as JSON alongside embeddings
- **Location**: `~/.toolsets/chroma/` by default

## Examples

### Basic Usage

```python
from toolsets import Toolset

toolset = Toolset()

# Add tools from multiple spaces
toolset.add("ResembleAI/chatterbox-turbo-demo")
toolset.add("fffiloni/diffusers-image-outpaint")

# Search for image editing tools
image_tools = toolset.search_tools("edit or modify images", k=5)
print(f"Found {len(image_tools)} image editing tools")

# Execute a tool
result = toolset.execute_tool(
    "diffusers-image-outpaint::outpaint",
    {
        "image": "path/to/image.jpg",
        "prompt": "extend the image",
        "mask": None
    }
)
```

### Filtering Tools

```python
toolset = Toolset()

# Only add specific tools from a space
toolset.add(
    "ResembleAI/chatterbox-turbo-demo",
    tools=["generate_speech", "list_voices"]
)
```

### Custom Persistence Directory

```python
toolset = Toolset(persist_directory="./my_tool_embeddings")
toolset.add("username/space-name")
```

### Launching for Testing

```python
toolset = Toolset()
toolset.add("ResembleAI/chatterbox-turbo-demo")
toolset.add("fffiloni/diffusers-image-outpaint")

# Launch interactive interface
toolset.launch(port=7860, share=False)

# Access at http://localhost:7860
# MCP server available at http://localhost:7860/gradio_api/mcp/schema
```

## Development

To set up the package for development, clone this repository and run:

```bash
pip install -e ".[dev]"
```

### Testing

Run tests with:

```bash
pytest
```

### Code Formatting

Format code using Ruff:

```bash
ruff check --fix --select I && ruff format
```

## How It Works

1. **Tool Registration**: When you call `add()`, the library connects to the MCP server and retrieves tool definitions (name, description, schema).

2. **Embedding Generation**: Each tool's name and description are combined into a text string (`"{name}: {description}"`) and embedded using the `all-MiniLM-L6-v2` sentence transformer model.

3. **Vector Storage**: Embeddings are stored in ChromaDB with metadata (tool ID, space URL, schema, etc.).

4. **Semantic Search**: When searching, your query is embedded using the same model, and ChromaDB performs cosine similarity search to find the most relevant tools.

5. **Dynamic Tool Injection**: Only the top-k most relevant tool schemas are returned, reducing context window usage compared to exposing all tools upfront.

6. **Tool Execution**: Tools are executed by proxying requests to their original MCP servers, maintaining the original functionality.

## Requirements

- Python 3.10+
- ChromaDB (for vector storage)
- sentence-transformers (for embeddings)
- Gradio (for interface and MCP server)
- httpx (for MCP client connections)

## Limitations

- Currently supports Gradio Spaces that expose MCP servers
- Embeddings are generated locally (requires model download on first use)
- Tool execution requires network access to original MCP servers

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License
