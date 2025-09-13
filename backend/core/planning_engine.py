# Comprehensive Planning Engine - Intelligent Business Workflow Orchestration

import json
import uuid
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from database.connection import db_manager
from backend.core.memory_manager import memory_manager
from backend.core.tool_registry import registry
import asyncio


class PlanStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    """Individual step in a plan"""
    step_id: str
    step_number: int
    action: str  # tool name or special action
    parameters: Dict[str, Any]
    dependencies: List[str] = None  # step_ids this depends on
    conditions: Dict[str, Any] = None  # conditional logic
    parallel_group: str = None  # steps that can run in parallel
    timeout_seconds: int = 300
    retry_count: int = 0
    max_retries: int = 2
    status: StepStatus = StepStatus.PENDING
    result: Dict[str, Any] = None
    error_message: str = None
    started_at: str = None
    completed_at: str = None


@dataclass
class ExecutionPlan:
    """Complete execution plan"""
    plan_id: str
    user_id: str
    goal: str
    description: str
    steps: List[PlanStep]
    status: PlanStatus = PlanStatus.PENDING
    created_at: str = None
    started_at: str = None
    completed_at: str = None
    total_steps: int = 0
    completed_steps: int = 0
    context: Dict[str, Any] = None
    escalation_rules: Dict[str, Any] = None
    approval_required: bool = False
    approved_by: str = None


class PlanningEngine:
    """
    Intelligent planning engine for complex business workflows
    """
    
    def __init__(self):
        self.business_templates = self._load_business_templates()
        self.running_plans = {}  # plan_id -> execution context
        self._create_planning_tables()
    
    def _create_planning_tables(self):
        """Create database tables for plan storage"""
        
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS execution_plans (
                plan_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                goal TEXT NOT NULL,
                description TEXT,
                plan_data TEXT NOT NULL, -- JSON serialized plan
                status TEXT DEFAULT 'pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                started_at DATETIME,
                completed_at DATETIME,
                approval_required BOOLEAN DEFAULT 0,
                approved_by TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        
        db_manager.execute_query("""
            CREATE TABLE IF NOT EXISTS plan_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id TEXT NOT NULL,
                step_id TEXT NOT NULL,
                step_number INTEGER,
                action TEXT,
                parameters TEXT, -- JSON
                result TEXT, -- JSON
                status TEXT,
                error_message TEXT,
                started_at DATETIME,
                completed_at DATETIME,
                FOREIGN KEY (plan_id) REFERENCES execution_plans(plan_id)
            )
        """)
        
        db_manager.execute_query("""
            CREATE INDEX IF NOT EXISTS idx_execution_plans_user ON execution_plans(user_id, status)
        """)
    
    def _load_business_templates(self) -> Dict[str, Any]:
        """Load predefined business process templates"""
        
        return {
            "invoice_investigation": {
                "description": "Comprehensive invoice failure investigation",
                "keywords": ["investigate", "invoice", "failed", "failure", "issues"],
                "steps": [
                    {
                        "action": "filter_data",
                        "params": {"dataset": "invoices", "status": "failed"},
                        "description": "Get all failed invoices"
                    },
                    {
                        "action": "_analyze_patterns",
                        "params": {"data": "{{step1.results}}"},
                        "description": "Analyze failure patterns",
                        "dependencies": ["step1"]
                    },
                    {
                        "action": "create_ticket", 
                        "params": {
                            "title": "Invoice Failure Investigation - {{step2.vendor_count}} vendors affected",
                            "description": "Found {{step1.filtered_records}} failed invoices requiring attention",
                            "priority": "high"
                        },
                        "description": "Create resolution ticket",
                        "dependencies": ["step1", "step2"]
                    }
                ],
                "escalation_rules": {
                    "critical_vendor_count > 5": {"notify": "cfo", "priority": "urgent"},
                    "failed_amount > 100000": {"escalate": "immediate"}
                }
            },
            
            "vendor_analysis": {
                "description": "Comprehensive vendor performance analysis",
                "keywords": ["vendor", "analyze", "performance", "issues"],
                "steps": [
                    {
                        "action": "filter_data",
                        "params": {"dataset": "invoices", "vendor": "{{vendor_name}}"},
                        "description": "Get vendor invoice history"
                    },
                    {
                        "action": "filter_data",
                        "params": {"dataset": "invoices", "vendor": "{{vendor_name}}", "status": "failed"},
                        "description": "Get vendor failures",
                        "parallel_group": "analysis"
                    },
                    {
                        "action": "_analyze_vendor_patterns",
                        "params": {
                            "all_invoices": "{{step1.results}}",
                            "failed_invoices": "{{step2.results}}"
                        },
                        "dependencies": ["step1", "step2"]
                    },
                    {
                        "action": "create_ticket",
                        "params": {
                            "title": "Vendor Analysis: {{vendor_name}}",
                            "description": "Performance analysis results: {{step3.summary}}",
                            "priority": "medium"
                        },
                        "dependencies": ["step3"]
                    }
                ]
            },
            
            "monthly_review": {
                "description": "Monthly business data review",
                "keywords": ["monthly", "review", "report", "summary"],
                "approval_required": True,
                "steps": [
                    {
                        "action": "filter_data",
                        "params": {"dataset": "invoices", "period": "last month"},
                        "parallel_group": "data_collection"
                    },
                    {
                        "action": "filter_data", 
                        "params": {"dataset": "sales", "period": "last month"},
                        "parallel_group": "data_collection"
                    },
                    {
                        "action": "_generate_summary",
                        "params": {
                            "invoices": "{{step1.results}}",
                            "sales": "{{step2.results}}"
                        },
                        "dependencies": ["step1", "step2"]
                    },
                    {
                        "action": "export_report",
                        "params": {"format": "pdf", "data": "{{step3.summary}}"},
                        "dependencies": ["step3"]
                    }
                ]
            }
        }
    
    def analyze_request(self, user_message: str, user_context) -> Dict[str, Any]:
        """Analyze user request to determine if it needs planning"""
        
        # Get user's memory context for better analysis
        memory_context = memory_manager.get_conversation_context(
            user_context.user_id, user_message
        )
        
        # Analyze complexity indicators
        complexity_indicators = {
            "multi_step_keywords": ["investigate", "resolve", "comprehensive", "complete", "full", "end-to-end"],
            "workflow_keywords": ["process", "workflow", "procedure", "steps", "plan"],
            "business_process_keywords": ["monthly", "quarterly", "audit", "compliance", "reporting"],
            "resolution_keywords": ["fix", "resolve", "handle", "address", "solve"],
            "analysis_keywords": ["analyze", "review", "examine", "study", "assess"]
        }
        
        message_lower = user_message.lower()
        complexity_score = 0
        matched_categories = []
        
        for category, keywords in complexity_indicators.items():
            if any(keyword in message_lower for keyword in keywords):
                complexity_score += 1
                matched_categories.append(category)
        
        # Check for template matches
        template_matches = []
        for template_name, template in self.business_templates.items():
            template_keywords = template.get("keywords", template_name.split("_"))
            if any(keyword in message_lower for keyword in template_keywords):
                template_matches.append(template_name)
        
        # Determine if planning is needed
        needs_planning = (
            complexity_score >= 2 or  # Multiple complexity indicators
            len(template_matches) > 0 or  # Matches business template
            "plan" in message_lower or "workflow" in message_lower
        )
        
        return {
            "needs_planning": needs_planning,
            "complexity_score": complexity_score,
            "matched_categories": matched_categories,
            "template_matches": template_matches,
            "confidence": min(complexity_score * 0.3 + len(template_matches) * 0.4, 1.0),
            "memory_context": memory_context
        }
    
    def create_plan(self, goal: str, user_context, template_name: str = None, 
                   custom_params: Dict[str, Any] = None) -> ExecutionPlan:
        """Create an execution plan based on goal and template"""
        
        plan_id = f"plan_{user_context.user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Use template or create custom plan
        if template_name and template_name in self.business_templates:
            template = self.business_templates[template_name]
            steps_data = template["steps"]
            description = template.get("description", goal)
            approval_required = template.get("approval_required", False)
            escalation_rules = template.get("escalation_rules", {})
        else:
            # Create simple single-step plan
            steps_data = [{"action": "analyze_request", "params": {"goal": goal}}]
            description = f"Execute: {goal}"
            approval_required = False
            escalation_rules = {}
        
        # Create plan steps
        steps = []
        for i, step_data in enumerate(steps_data, 1):
            step_id = f"{plan_id}_step_{i}"
            
            # Apply custom parameters
            params = step_data.get("params", {})
            if custom_params:
                params.update(custom_params)
            
            step = PlanStep(
                step_id=step_id,
                step_number=i,
                action=step_data["action"],
                parameters=params,
                dependencies=step_data.get("dependencies", []),
                conditions=step_data.get("conditions"),
                parallel_group=step_data.get("parallel_group"),
                timeout_seconds=step_data.get("timeout", 300),
                max_retries=step_data.get("max_retries", 2)
            )
            steps.append(step)
        
        # Create execution plan
        plan = ExecutionPlan(
            plan_id=plan_id,
            user_id=user_context.user_id,
            goal=goal,
            description=description,
            steps=steps,
            total_steps=len(steps),
            created_at=datetime.now().isoformat(),
            approval_required=approval_required,
            escalation_rules=escalation_rules,
            context={"template_used": template_name, "custom_params": custom_params}
        )
        
        # Store plan in database
        self._store_plan(plan)
        
        return plan
    
    def _store_plan(self, plan: ExecutionPlan):
        """Store execution plan in database"""
        
        db_manager.execute_query("""
            INSERT INTO execution_plans (
                plan_id, user_id, goal, description, plan_data, 
                status, approval_required
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            plan.plan_id,
            plan.user_id,
            plan.goal,
            plan.description,
            json.dumps(asdict(plan), default=str),
            plan.status,
            plan.approval_required
        ))
    
    def execute_plan_sync(self, plan_id: str, user_context) -> Dict[str, Any]:
        """Synchronous version of plan execution for simple use"""
        
        # Load plan
        plan_data = db_manager.execute_query("""
            SELECT plan_data FROM execution_plans WHERE plan_id = ?
        """, (plan_id,), fetch_one=True)
        
        if not plan_data:
            return {"success": False, "error": "Plan not found"}
        
        plan_dict = json.loads(plan_data['plan_data'])
        
        # Reconstruct plan object
        steps = []
        for step_data in plan_dict['steps']:
            step = PlanStep(**step_data)
            steps.append(step)
        
        plan_dict['steps'] = steps
        plan = ExecutionPlan(**plan_dict)
        
        # Check approval if required
        if plan.approval_required:
            approval_check = db_manager.execute_query("""
                SELECT approved_by FROM execution_plans 
                WHERE plan_id = ? AND approved_by IS NOT NULL
            """, (plan_id,), fetch_one=True)
            
            if not approval_check:
                return {"success": False, "error": "Plan requires approval", "plan_id": plan_id}
        
        # Start execution
        plan.status = PlanStatus.RUNNING
        plan.started_at = datetime.now().isoformat()
        
        try:
            # Execute steps sequentially for simplicity
            execution_results = []
            step_results = {}
            
            for step in plan.steps:
                # Check dependencies
                if step.dependencies:
                    deps_met = all(dep.replace('step', f'{plan_id}_step_') in step_results 
                                 for dep in step.dependencies)
                    if not deps_met:
                        step.status = StepStatus.SKIPPED
                        continue
                
                # Execute step
                result = self._execute_step_sync(step, user_context, step_results)
                step_results[step.step_id] = result
                execution_results.append(result)
                
                if not result.get("success", False):
                    break
            
            # Update final status
            if all(step.status in [StepStatus.COMPLETED, StepStatus.SKIPPED] for step in plan.steps):
                plan.status = PlanStatus.COMPLETED
            else:
                plan.status = PlanStatus.FAILED
            
            plan.completed_at = datetime.now().isoformat()
            
            # Store final results
            self._update_plan_status(plan)
            
            return {
                "success": plan.status == PlanStatus.COMPLETED,
                "plan_id": plan_id,
                "status": plan.status,
                "completed_steps": sum(1 for step in plan.steps if step.status == StepStatus.COMPLETED),
                "total_steps": len(plan.steps),
                "results": execution_results,
                "execution_time": plan.completed_at
            }
            
        except Exception as e:
            plan.status = PlanStatus.FAILED
            plan.completed_at = datetime.now().isoformat()
            self._update_plan_status(plan)
            
            return {
                "success": False,
                "plan_id": plan_id,
                "error": str(e),
                "completed_steps": sum(1 for step in plan.steps if step.status == StepStatus.COMPLETED),
                "total_steps": len(plan.steps)
            }
    
    def _execute_step_sync(self, step: PlanStep, user_context, step_results: Dict) -> Dict[str, Any]:
        """Execute a single plan step synchronously"""
        
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        
        try:
            # Resolve parameter placeholders
            resolved_params = self._resolve_parameters(step.parameters, step_results)
            
            # Execute the step
            if step.action.startswith("_"):
                # Internal planning engine action
                result = self._execute_internal_action_sync(step.action, resolved_params, user_context)
            else:
                # External tool execution
                tool_result = registry.execute_tool(step.action, resolved_params, user_context)
                result = {
                    "success": tool_result.status == "success",
                    "data": tool_result.data,
                    "message": tool_result.message,
                    "tool_used": step.action
                }
            
            step.status = StepStatus.COMPLETED
            step.result = result
            
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error_message = str(e)
            result = {"success": False, "error": str(e)}
        
        finally:
            step.completed_at = datetime.now().isoformat()
            self._store_step_execution(step)
        
        return result
    
    def _resolve_parameters(self, params: Dict[str, Any], step_results: Dict) -> Dict[str, Any]:
        """Resolve parameter placeholders with actual values"""
        
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                # Extract reference like "{{step1.results}}"
                ref = value[2:-2]
                if "." in ref:
                    step_ref, field = ref.split(".", 1)
                    # Convert step references
                    if step_ref.startswith("step"):
                        step_num = step_ref.replace("step", "")
                        actual_step_id = None
                        for step_id in step_results.keys():
                            if step_id.endswith(f"_step_{step_num}"):
                                actual_step_id = step_id
                                break
                        
                        if actual_step_id and actual_step_id in step_results:
                            step_data = step_results[actual_step_id]
                            resolved[key] = self._extract_nested_value(step_data, field)
                        else:
                            resolved[key] = value  # Keep original if not found
                    else:
                        if step_ref in step_results:
                            step_data = step_results[step_ref]
                            resolved[key] = self._extract_nested_value(step_data, field)
                        else:
                            resolved[key] = value
                else:
                    resolved[key] = step_results.get(ref, value)
            else:
                resolved[key] = value
        
        return resolved
    
    def _extract_nested_value(self, data: Dict, path: str) -> Any:
        """Extract nested value using dot notation"""
        
        keys = path.split(".")
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _execute_internal_action_sync(self, action: str, params: Dict, user_context) -> Dict[str, Any]:
        """Execute internal planning engine actions synchronously"""
        
        if action == "_analyze_patterns":
            # Analyze data patterns
            data = params.get("data", {})
            patterns = self._analyze_data_patterns(data)
            return {"success": True, "patterns": patterns, **patterns}
        
        elif action == "_analyze_vendor_patterns":
            # Analyze vendor-specific patterns
            all_invoices = params.get("all_invoices", {})
            failed_invoices = params.get("failed_invoices", {})
            
            analysis = self._analyze_vendor_performance(all_invoices, failed_invoices)
            return {"success": True, "analysis": analysis, "summary": analysis.get("summary", "")}
        
        elif action == "_generate_summary":
            # Generate business summary
            invoices = params.get("invoices", {})
            sales = params.get("sales", {})
            
            summary = self._generate_business_summary(invoices, sales)
            return {"success": True, "summary": summary}
        
        elif action == "_notify_stakeholders":
            # Send notifications (mock)
            return {"success": True, "notifications_sent": ["admin", "manager"]}
        
        else:
            return {"success": False, "error": f"Unknown internal action: {action}"}
    
    def _analyze_data_patterns(self, data: Dict) -> Dict[str, Any]:
        """Analyze patterns in data results"""
        
        if "results" in data:
            results = data["results"]
            if isinstance(results, list):
                # Analyze vendor patterns
                vendors = {}
                statuses = {}
                
                for item in results:
                    vendor = item.get("vendor_name", "unknown")
                    status = item.get("status", "unknown")
                    
                    vendors[vendor] = vendors.get(vendor, 0) + 1
                    statuses[status] = statuses.get(status, 0) + 1
                
                return {
                    "vendor_count": len(vendors),
                    "top_vendor": max(vendors.items(), key=lambda x: x[1])[0] if vendors else None,
                    "status_distribution": statuses,
                    "total_items": len(results)
                }
        
        return {"total_items": 0, "vendor_count": 0}
    
    def _analyze_vendor_performance(self, all_invoices: Dict, failed_invoices: Dict) -> Dict[str, Any]:
        """Analyze vendor performance"""
        
        total = all_invoices.get("filtered_records", 0)
        failed = failed_invoices.get("filtered_records", 0)
        
        failure_rate = (failed / total * 100) if total > 0 else 0
        
        return {
            "total_invoices": total,
            "failed_invoices": failed,
            "failure_rate": round(failure_rate, 2),
            "summary": f"Vendor has {failure_rate:.1f}% failure rate ({failed}/{total} invoices)"
        }
    
    def _generate_business_summary(self, invoices: Dict, sales: Dict) -> Dict[str, Any]:
        """Generate business summary"""
        
        return {
            "invoices_processed": invoices.get("filtered_records", 0),
            "sales_recorded": sales.get("filtered_records", 0),
            "period": "last_month",
            "summary_text": f"Monthly review: {invoices.get('filtered_records', 0)} invoices, {sales.get('filtered_records', 0)} sales"
        }
    
    def _store_step_execution(self, step: PlanStep):
        """Store step execution details"""
        
        plan_id = step.step_id.split("_step_")[0]  # Extract plan_id
        
        db_manager.execute_query("""
            INSERT OR REPLACE INTO plan_executions (
                plan_id, step_id, step_number, action, parameters,
                result, status, error_message, started_at, completed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id,
            step.step_id,
            step.step_number,
            step.action,
            json.dumps(step.parameters),
            json.dumps(step.result) if step.result else None,
            step.status,
            step.error_message,
            step.started_at,
            step.completed_at
        ))
    
    def _update_plan_status(self, plan: ExecutionPlan):
        """Update plan status in database"""
        
        db_manager.execute_query("""
            UPDATE execution_plans 
            SET status = ?, started_at = ?, completed_at = ?, plan_data = ?
            WHERE plan_id = ?
        """, (
            plan.status,
            plan.started_at,
            plan.completed_at,
            json.dumps(asdict(plan), default=str),
            plan.plan_id
        ))
    
    def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """Get current plan execution status"""
        
        plan_info = db_manager.execute_query("""
            SELECT status, goal, description, plan_data FROM execution_plans 
            WHERE plan_id = ?
        """, (plan_id,), fetch_one=True)
        
        if not plan_info:
            return {"error": "Plan not found"}
        
        # Get step executions
        step_executions = db_manager.execute_query("""
            SELECT step_number, action, status, error_message, started_at, completed_at
            FROM plan_executions
            WHERE plan_id = ?
            ORDER BY step_number
        """, (plan_id,))
        
        return {
            "plan_id": plan_id,
            "status": plan_info["status"],
            "goal": plan_info["goal"], 
            "description": plan_info["description"],
            "steps": [dict(step) for step in step_executions]
        }
    
    def get_user_plans(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's execution plans"""
        
        plans = db_manager.execute_query("""
            SELECT plan_id, goal, description, status, created_at, started_at, completed_at
            FROM execution_plans
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """, (user_id, limit))
        
        return [dict(plan) for plan in plans]

# Global planning engine instance
planning_engine = PlanningEngine()