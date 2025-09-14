# Simple tools package - import all available tools

from .filter_data_tool import FilterDataTool
from .export_tool import ExportTool
from .ticket_tool import TicketTool
from .view_tickets_tool import ViewTicketsTool
from .update_ticket_tool import UpdateTicketTool
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter

# Registry of all available tools
AVAILABLE_TOOLS = {
    "filter_data": FilterDataTool,
    "export_report": ExportTool,
    "create_ticket": TicketTool,
    "view_tickets": ViewTicketsTool,
    "update_ticket": UpdateTicketTool
}

def get_tool(tool_name: str) -> BaseTool:
    """Get a tool instance by name"""
    if tool_name in AVAILABLE_TOOLS:
        return AVAILABLE_TOOLS[tool_name]()
    raise ValueError(f"Tool '{tool_name}' not found")

def get_all_tools() -> dict:
    """Get all available tools as instances"""
    return {name: tool_class() for name, tool_class in AVAILABLE_TOOLS.items()}