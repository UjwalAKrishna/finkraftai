# Simple filter data tool - basic implementation

from typing import Dict, Any, List
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter


class FilterDataTool(BaseTool):
    """Simple tool for filtering data - returns mock results for demo"""
    
    @property
    def name(self) -> str:
        return "filter_data"
    
    @property
    def description(self) -> str:
        return "Filter dataset by basic criteria"
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="dataset", 
                type="string",
                required=True,
                description="Dataset to filter (invoices, sales, etc)"
            ),
            ToolParameter(
                name="period",
                type="string", 
                required=False,
                description="Time period (last month, last week, etc)"
            ),
            ToolParameter(
                name="vendor",
                type="string",
                required=False,
                description="Vendor name to filter by"
            ),
            ToolParameter(
                name="status",
                type="string",
                required=False,
                description="Status to filter by"
            )
        ]
    
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Simple mock implementation that returns sample filtered data"""
        
        dataset = params.get("dataset", "invoices")
        period = params.get("period", "all")
        vendor = params.get("vendor")
        status = params.get("status")
        
        # Mock filtered results
        mock_data = {
            "dataset": dataset,
            "period": period,
            "filters_applied": {
                "vendor": vendor,
                "status": status
            },
            "total_records": 124,
            "filtered_records": 7,
            "results": [
                {"id": 1, "vendor": vendor or "IndiSky", "status": status or "failed", "amount": 1500},
                {"id": 2, "vendor": vendor or "IndiSky", "status": status or "failed", "amount": 2300},
                {"id": 3, "vendor": vendor or "IndiSky", "status": status or "failed", "amount": 980}
            ]
        }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=mock_data,
            message=f"Found {mock_data['filtered_records']} {dataset} matching filters"
        )