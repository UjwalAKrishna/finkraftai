# Simple export tool - basic implementation

from typing import Dict, Any, List
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter


class ExportTool(BaseTool):
    """Simple tool for exporting data - returns mock download link"""
    
    @property
    def name(self) -> str:
        return "export_report"
    
    @property
    def description(self) -> str:
        return "Export data as CSV or Excel file"
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="dataset",
                type="string",
                required=True,
                description="Dataset to export (invoices, sales, etc)"
            ),
            ToolParameter(
                name="format",
                type="string",
                required=False,
                description="Export format (csv, excel)",
                default="csv"
            ),
            ToolParameter(
                name="status",
                type="string",
                required=False,
                description="Filter by status (failed, processed, pending)"
            ),
            ToolParameter(
                name="vendor",
                type="string",
                required=False,
                description="Filter by vendor name"
            ),
            ToolParameter(
                name="period",
                type="string",
                required=False,
                description="Filter by time period (last month, last week, today)"
            )
        ]
    
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Export data to downloadable file"""
        
        dataset = params.get("dataset", "data")
        format_type = params.get("format", "csv")
        
        try:
            # Get data from the last filter operation or fetch fresh data
            data_to_export = self._get_data_for_export(dataset, params, user_context)
            
            if not data_to_export:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    message="No data available to export. Please filter data first."
                )
            
            # Generate filename with timestamp
            import time
            timestamp = int(time.time())
            filename = f"{dataset}_export_{timestamp}.{format_type}"
            
            # Create exports directory if it doesn't exist
            import os
            exports_dir = "exports"
            os.makedirs(exports_dir, exist_ok=True)
            
            file_path = os.path.join(exports_dir, filename)
            
            # Export data based on format
            if format_type.lower() == 'csv':
                rows_exported = self._export_to_csv(data_to_export, file_path)
            else:
                rows_exported = self._export_to_csv(data_to_export, file_path)  # Default to CSV
            
            # Calculate file size
            file_size = os.path.getsize(file_path)
            size_mb = round(file_size / (1024 * 1024), 2)
            
            export_result = {
                "dataset": dataset,
                "format": format_type,
                "filename": filename,
                "file_path": file_path,
                "download_url": f"/api/download/{filename}",
                "size": f"{size_mb} MB",
                "rows_exported": rows_exported
            }
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                data=export_result,
                message=f"✅ Exported {rows_exported} rows to **{filename}** ({size_mb} MB). [Download here](/api/download/{filename})"
            )
            
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Export failed: {str(e)}"
            )
    
    def _get_data_for_export(self, dataset: str, params: Dict[str, Any], user_context: UserContext) -> List[Dict]:
        """Get data for export by querying the database with filters"""
        
        try:
            from backend.core.database_connector import db_connector
            
            if dataset == "invoices":
                # Base query with vendor join
                base_query = """
                SELECT 
                    i.invoice_number,
                    v.vendor_name,
                    v.vendor_code,
                    i.invoice_date,
                    i.total_amount,
                    i.tax_amount,
                    i.net_amount,
                    i.status,
                    i.payment_status,
                    i.gstin_verified,
                    i.error_message
                FROM invoices i
                JOIN vendors v ON i.vendor_id = v.id
                WHERE 1=1
                """
                
                conditions = []
                query_params = []
                
                # Apply filters from parameters
                status = params.get("status")
                if status:
                    conditions.append("i.status = ?")
                    query_params.append(status.lower())
                
                vendor = params.get("vendor")
                if vendor:
                    conditions.append("(v.vendor_name LIKE ? OR v.vendor_code LIKE ?)")
                    vendor_pattern = f"%{vendor}%"
                    query_params.extend([vendor_pattern, vendor_pattern])
                
                # Date filtering
                period = params.get("period")
                if period:
                    date_condition, date_param = self._build_date_condition(period, "i.invoice_date")
                    if date_condition:
                        conditions.append(date_condition)
                        if date_param:
                            query_params.append(date_param)
                
                # Build final query
                if conditions:
                    query = base_query + " AND " + " AND ".join(conditions)
                else:
                    query = base_query
                
                query += " ORDER BY i.invoice_date DESC"
                
                results = db_connector.execute_query(query, tuple(query_params))
                return [dict(row) for row in results]
                
            elif dataset == "sales":
                query = """
                SELECT 
                    s.sale_date,
                    s.customer_name,
                    p.product_name,
                    p.category,
                    s.quantity,
                    s.unit_price,
                    s.total_amount,
                    s.region,
                    s.salesperson,
                    s.status
                FROM sales s
                LEFT JOIN products p ON s.product_id = p.id
                ORDER BY s.sale_date DESC
                """
                
                results = db_connector.execute_query(query)
                return [dict(row) for row in results]
                
            else:
                return []
                
        except Exception as e:
            print(f"Error getting data for export: {e}")
            return []
    
    def _export_to_csv(self, data: List[Dict], file_path: str) -> int:
        """Export data to CSV file"""
        
        import csv
        
        if not data:
            return 0
        
        # Get column headers from first row
        headers = list(data[0].keys())
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=headers)
            writer.writeheader()
            writer.writerows(data)
        
        return len(data)
    
    def _build_date_condition(self, period: str, date_column: str) -> tuple:
        """Build date filtering condition"""
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        
        if period.lower() == "today":
            return f"{date_column} = ?", today.strftime('%Y-%m-%d')
        elif period.lower() == "last week":
            start_date = today - timedelta(days=7)
            return f"{date_column} >= ?", start_date.strftime('%Y-%m-%d')
        elif period.lower() == "last month":
            start_date = today - timedelta(days=30)
            return f"{date_column} >= ?", start_date.strftime('%Y-%m-%d')
        elif period.lower() == "last 30 days":
            start_date = today - timedelta(days=30)
            return f"{date_column} >= ?", start_date.strftime('%Y-%m-%d')
        elif period.lower() == "last 90 days":
            start_date = today - timedelta(days=90)
            return f"{date_column} >= ?", start_date.strftime('%Y-%m-%d')
        else:
            return None, None