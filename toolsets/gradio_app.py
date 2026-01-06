import gradio as gr
from typing import List, Dict, Any
import json
from .toolset import Toolset


def create_gradio_app(toolset: Toolset):
    def search_tools(query: str, k: int = 5) -> str:
        if not query.strip():
            return "Please enter a query to search for tools."
        try:
            tools = toolset.search_tools(query, k=k)
            if not tools:
                return "No tools found matching your query."
            result = []
            for i, tool in enumerate(tools, 1):
                result.append(f"{i}. **{tool['name']}** (from {tool['space_name']})")
                result.append(f"   Description: {tool['description']}")
                result.append(f"   Tool ID: `{tool['id']}`")
                result.append(f"   Distance: {tool.get('distance', 'N/A'):.4f}")
                result.append("")
            return "\n".join(result)
        except Exception as e:
            return f"Error searching tools: {str(e)}"

    def execute_tool(tool_id: str, parameters_json: str) -> str:
        if not tool_id.strip():
            return "Please enter a tool ID."
        try:
            if parameters_json.strip():
                parameters = json.loads(parameters_json)
            else:
                parameters = {}
            result = toolset.execute_tool(tool_id, parameters)
            return json.dumps(result, indent=2)
        except json.JSONDecodeError as e:
            return f"Invalid JSON in parameters: {str(e)}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def get_tool_schema(tool_id: str) -> str:
        if not tool_id.strip():
            return "Please enter a tool ID."
        try:
            all_tool_ids = toolset.vector_store.get_all_tools()
            if tool_id not in all_tool_ids:
                return f"Tool {tool_id} not found."
            schema = toolset.vector_store.get_tool_schema(tool_id)
            if not schema:
                return f"Schema not found for tool {tool_id}."
            return json.dumps(schema, indent=2)
        except Exception as e:
            return f"Error retrieving schema: {str(e)}"

    with gr.Blocks(title="Toolsets MCP Server") as app:
        gr.Markdown("# Toolsets MCP Server")
        gr.Markdown("Search for tools using semantic search and execute them.")

        with gr.Tab("Search Tools"):
            with gr.Row():
                with gr.Column():
                    search_query = gr.Textbox(
                        label="Query",
                        placeholder="Enter a description of what you want to do...",
                        lines=2
                    )
                    search_k = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                        label="Number of results (k)"
                    )
                    search_btn = gr.Button("Search", variant="primary")
                with gr.Column():
                    search_results = gr.Markdown(label="Search Results")

            search_btn.click(
                fn=search_tools,
                inputs=[search_query, search_k],
                outputs=search_results
            )
            search_query.submit(
                fn=search_tools,
                inputs=[search_query, search_k],
                outputs=search_results
            )

        with gr.Tab("Execute Tool"):
            with gr.Row():
                with gr.Column():
                    tool_id_input = gr.Textbox(
                        label="Tool ID",
                        placeholder="space_name::tool_name",
                        lines=1
                    )
                    tool_params = gr.Textbox(
                        label="Parameters (JSON)",
                        placeholder='{"key": "value"}',
                        lines=5
                    )
                    execute_btn = gr.Button("Execute", variant="primary")
                with gr.Column():
                    tool_result = gr.Code(
                        label="Result",
                        language="json"
                    )

            execute_btn.click(
                fn=execute_tool,
                inputs=[tool_id_input, tool_params],
                outputs=tool_result
            )

        with gr.Tab("Get Tool Schema"):
            with gr.Row():
                with gr.Column():
                    schema_tool_id = gr.Textbox(
                        label="Tool ID",
                        placeholder="space_name::tool_name",
                        lines=1
                    )
                    schema_btn = gr.Button("Get Schema", variant="primary")
                with gr.Column():
                    schema_output = gr.Code(
                        label="Tool Schema",
                        language="json"
                    )

            schema_btn.click(
                fn=get_tool_schema,
                inputs=[schema_tool_id],
                outputs=schema_output
            )

        with gr.Tab("Info"):
            gr.Markdown("## Registered Spaces")
            spaces_info = gr.Markdown()
            app.load(
                fn=lambda: "\n".join([
                    f"- **{name}**: {url}"
                    for name, url in toolset._spaces.items()
                ]) if toolset._spaces else "No spaces registered yet.",
                outputs=spaces_info
            )

    return app

