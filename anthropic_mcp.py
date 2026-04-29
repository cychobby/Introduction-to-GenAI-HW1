import asyncio
import os
from threading import Thread

from anthropic import Anthropic
from anthropic.lib.tools.mcp import mcp_tool
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.fastmcp import FastMCP

from tools import ToolExecutor

MCP_SERVER_HOST = "127.0.0.1"
MCP_SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8001"))
MCP_SERVER_URL = f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/mcp"
_mcp_server_thread = None


def ensure_mcp_server_running() -> None:
    """Start a local MCP server process if it is not already running."""
    global _mcp_server_thread
    if _mcp_server_thread is not None and _mcp_server_thread.is_alive():
        return

    executor = ToolExecutor()
    server = FastMCP(
        name="LocalMCP",
        instructions=(
            "A local tool execution server used by Anthropic MCP. "
            "It exposes calculator, web_search, execute_code, file_operations, and fetch tools."
        ),
        host=MCP_SERVER_HOST,
        port=MCP_SERVER_PORT,
        streamable_http_path="/mcp",
        debug=False,
    )

    server.add_tool(
        executor.calculator,
        name="calculator",
        title="Calculator",
        description="Perform mathematical calculations and solve equations.",
    )
    server.add_tool(
        executor.web_search,
        name="web_search",
        title="Web Search",
        description="Search the internet for current information and news.",
    )
    server.add_tool(
        executor.execute_code,
        name="execute_code",
        title="Execute Code",
        description="Execute Python code in a safe environment and return the output.",
    )
    server.add_tool(
        executor.file_operations,
        name="file_operations",
        title="File Operations",
        description="Read, write, or list directory contents within allowed paths.",
    )
    server.add_tool(
        executor.fetch,
        name="fetch",
        title="Fetch URL",
        description="Fetch the content of a URL and return the response status, headers, and body.",
    )

    def run_server() -> None:
        server.run(transport="streamable-http")

    _mcp_server_thread = Thread(target=run_server, daemon=True)
    _mcp_server_thread.start()


def _extract_text_from_beta_message(message: object) -> str:
    if hasattr(message, "parsed_output") and message.parsed_output is not None:
        return str(message.parsed_output)

    texts = []
    for block in getattr(message, "content", []) or []:
        if hasattr(block, "text") and block.text:
            texts.append(block.text)
        elif hasattr(block, "parsed_output") and block.parsed_output is not None:
            texts.append(str(block.parsed_output))
        elif hasattr(block, "output_text") and block.output_text:
            texts.append(block.output_text)
        elif hasattr(block, "value") and block.value is not None:
            texts.append(str(block.value))

    return "\n".join(texts).strip()


async def _run_anthropic_mcp_async(
    messages: list[dict],
    model: str,
    api_key: str,
    temperature: float,
    use_tools: bool,
) -> str:
    async with streamable_http_client(MCP_SERVER_URL) as (read_stream, write_stream, _):
        session = ClientSession(read_stream, write_stream)
        await session.initialize()
        tools = []
        if use_tools:
            tools_result = await session.list_tools()
            tools = [mcp_tool(tool, session) for tool in tools_result.tools]

        client = Anthropic(api_key=api_key)
        request_params = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        if use_tools:
            request_params["tools"] = tools
            request_params["tool_choice"] = "auto"
            request_params["mcp_servers"] = [{"url": MCP_SERVER_URL}]

        runner = client.beta.messages.tool_runner(**request_params)
        result = runner.until_done()
        return _extract_text_from_beta_message(result)


def run_anthropic_mcp(
    messages: list[dict],
    model: str,
    api_key: str,
    temperature: float,
    use_tools: bool,
) -> str:
    if not api_key:
        raise ValueError("Missing ANTHROPIC_API_KEY environment variable for Anthropic MCP.")
    ensure_mcp_server_running()
    return asyncio.run(_run_anthropic_mcp_async(messages, model, api_key, temperature, use_tools))
