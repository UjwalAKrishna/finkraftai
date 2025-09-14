# Real data filter tool - queries external business database

from typing import Dict, Any, List
from datetime import datetime, timedelta
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter


class FilterDataTool(BaseTool):
    """Tool for filtering real business data from external database"""
    
    @property
    def name(self) -> str:
        return "filter_data"
    
    @property
    def description(self) -> str:
        return "Filter business data (invoices, sales, transactions) by various criteria"
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="dataset", 
                type="string",
                required=True,
                description="Dataset to filter (invoices, sales, transactions)"
            ),
            ToolParameter(
                name="period",
                type="string", 
                required=False,
                description="Time period (last month, last week, today, last 30 days)"
            ),
            ToolParameter(
                name="vendor",
                type="string",
                required=False,
                description="Vendor name or code to filter by"
            ),
            ToolParameter(
                name="status",
                type="string",
                required=False,
                description="Status to filter by (failed, processed, pending, etc.)"
            ),
            ToolParameter(
                name="customer",
                type="string",
                required=False,
                description="Customer name to filter by"
            ),
            ToolParameter(
                name="amount_min",
                type="string",
                required=False,
                description="Minimum amount filter"
            ),
            ToolParameter(
                name="amount_max",
                type="string",
                required=False,
                description="Maximum amount filter"
            )
        ]
    
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Filter real business data based on parameters"""
        
        dataset = params.get("dataset", "invoices").lower()
        
        try:
            if dataset == "invoices":
                return self._filter_invoices(params, user_context)
            elif dataset == "sales":
                return self._filter_sales(params, user_context)
            elif dataset == "transactions":
                return self._filter_transactions(params, user_context)
            else:
                return ToolResult(
                    status=ToolResultStatus.ERROR,
                    message=f"Unsupported dataset: {dataset}. Available: invoices, sales, transactions"
                )
                
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Error filtering data: {str(e)}"
            )
    
    def _filter_invoices(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Filter invoice data"""
        
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
        
        # Date filtering
        period = params.get("period")
        if period:
            date_condition, date_param = self._build_date_condition(period, "i.invoice_date")
            if date_condition:
                conditions.append(date_condition)
                if date_param:
                    query_params.append(date_param)
        
        # Vendor filtering
        vendor = params.get("vendor")
        if vendor:
            conditions.append("(v.vendor_name LIKE ? OR v.vendor_code LIKE ?)")
            vendor_pattern = f"%{vendor}%"
            query_params.extend([vendor_pattern, vendor_pattern])
        
        # Status filtering
        status = params.get("status")
        if status:
            conditions.append("i.status = ?")
            query_params.append(status.lower())
        
        # Amount filtering
        amount_min = params.get("amount_min")
        if amount_min:
            try:
                conditions.append("i.total_amount >= ?")
                query_params.append(float(amount_min))
            except ValueError:
                pass
        
        amount_max = params.get("amount_max")
        if amount_max:
            try:
                conditions.append("i.total_amount <= ?")
                query_params.append(float(amount_max))
            except ValueError:
                pass
        
        # Build final query
        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query
        
        query += " ORDER BY i.invoice_date DESC LIMIT 100"
        
        # Execute query
        import sqlite3
        import os
        
        # Connect to business database
        db_path = "business_data.db"
        if not os.path.exists(db_path):
            # Create the database if it doesn't exist
            from external_db.business_data import create_business_database
            create_business_database(db_path)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Execute main query
            cursor.execute(query, tuple(query_params))
            results = [dict(row) for row in cursor.fetchall()]
            
            # Get total count (before limit) - simplified
            count_query = """
            SELECT COUNT(*) as total
            FROM invoices i
            JOIN vendors v ON i.vendor_id = v.id
            WHERE 1=1
            """
            if conditions:
                count_query = count_query + " AND " + " AND ".join(conditions)
            
            cursor.execute(count_query, tuple(query_params))
            count_result = dict(cursor.fetchone())
        finally:
            conn.close()
        total_count = count_result['total'] if count_result else 0
        
        # Format response
        response_data = {
            "dataset": "invoices",
            "filters_applied": {
                "period": period,
                "vendor": vendor,
                "status": status,
                "amount_min": amount_min,
                "amount_max": amount_max
            },
            "total_records": total_count,
            "filtered_records": len(results),
            "showing_records": min(len(results), 100),
            "results": results
        }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=response_data,
            message=f"Found {len(results)} invoices matching filters (total: {total_count})"
        )
    
    def _filter_sales(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Filter sales data"""
        
        base_query = """
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
        WHERE 1=1
        """
        
        conditions = []
        query_params = []
        
        # Date filtering
        period = params.get("period")
        if period:
            date_condition, date_param = self._build_date_condition(period, "s.sale_date")
            if date_condition:
                conditions.append(date_condition)
                if date_param:
                    query_params.append(date_param)
        
        # Customer filtering
        customer = params.get("customer")
        if customer:
            conditions.append("s.customer_name LIKE ?")
            query_params.append(f"%{customer}%")
        
        # Build and execute query
        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query
        
        query += " ORDER BY s.sale_date DESC LIMIT 100"
        
        import sqlite3
        import os
        
        # Connect to business database
        db_path = "business_data.db"
        if not os.path.exists(db_path):
            from external_db.business_data import create_business_database
            create_business_database(db_path)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, tuple(query_params))
            results = [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
        
        response_data = {
            "dataset": "sales",
            "filters_applied": params,
            "filtered_records": len(results),
            "results": results
        }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=response_data,
            message=f"Found {len(results)} sales records"
        )
    
    def _filter_transactions(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Filter transaction data"""
        
        base_query = """
        SELECT 
            t.transaction_id,
            t.transaction_date,
            t.amount,
            t.payment_method,
            t.reference_number,
            t.status,
            i.invoice_number,
            v.vendor_name
        FROM transactions t
        LEFT JOIN invoices i ON t.invoice_id = i.id
        LEFT JOIN vendors v ON i.vendor_id = v.id
        WHERE 1=1
        """
        
        conditions = []
        query_params = []
        
        # Date filtering
        period = params.get("period")
        if period:
            date_condition, date_param = self._build_date_condition(period, "t.transaction_date")
            if date_condition:
                conditions.append(date_condition)
                if date_param:
                    query_params.append(date_param)
        
        # Status filtering
        status = params.get("status")
        if status:
            conditions.append("t.status = ?")
            query_params.append(status.lower())
        
        # Build and execute query
        if conditions:
            query = base_query + " AND " + " AND ".join(conditions)
        else:
            query = base_query
        
        query += " ORDER BY t.transaction_date DESC LIMIT 100"
        
        import sqlite3
        import os
        
        # Connect to business database
        db_path = "business_data.db"
        if not os.path.exists(db_path):
            from external_db.business_data import create_business_database
            create_business_database(db_path)
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, tuple(query_params))
            results = [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
        
        response_data = {
            "dataset": "transactions",
            "filters_applied": params,
            "filtered_records": len(results),
            "results": results
        }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=response_data,
            message=f"Found {len(results)} transactions"
        )
    
    def _build_date_condition(self, period: str, date_column: str) -> tuple:
        """Build date filtering condition"""
        
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