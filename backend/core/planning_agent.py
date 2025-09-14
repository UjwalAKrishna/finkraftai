# Advanced Planning and Execution Agent
# Implements proper multi-step planning with detailed trace visibility

import json
import time
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class PlanStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class PlanType(str, Enum):
    SINGLE_TOOL = "single_tool"
    MULTI_STEP = "multi_step"
    ANALYSIS = "analysis"
    FOLLOW_UP = "follow_up"

@dataclass
class PlanStep:
    step_id: str
    step_number: int
    description: str
    tool_name: str
    parameters: Dict[str, Any]
    reasoning: str
    depends_on: List[str] = None
    status: PlanStepStatus = PlanStepStatus.PENDING
    result: Dict[str, Any] = None
    execution_time_ms: int = 0
    error_message: str = None

@dataclass
class ExecutionPlan:
    plan_id: str
    plan_type: PlanType
    user_message: str
    goal: str
    steps: List[PlanStep]
    context: Dict[str, Any] = None
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    start_time: float = None
    end_time: float = None

class PlanningAgent:
    """Advanced planning agent with multi-step execution and detailed tracing"""
    
    def __init__(self):
        self.llm = None
        self.trace_service = None
        self.registry = None
        self._init_dependencies()
    
    def _init_dependencies(self):
        """Initialize dependencies"""
        try:
            from backend.core.llm_provider import llm_manager
            from backend.services.trace_service import trace_service
            from backend.core.tool_registry import registry
            
            self.llm = llm_manager
            self.trace_service = trace_service
            self.registry = registry
            print(f"✅ Planning agent dependencies initialized successfully")
        except ImportError as e:
            print(f"❌ Warning: Could not import dependencies: {e}")
            import traceback
            traceback.print_exc()
    
    def create_plan(self, message: str, user_context, conversation_history: List[Dict] = None) -> ExecutionPlan:
        """Create an execution plan based on user message and context"""
        
        plan_id = f"plan_{user_context.user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Analyze message to determine plan type and steps
        plan_analysis = self._analyze_user_request(message, user_context, conversation_history)
        
        # Create plan steps
        steps = self._create_plan_steps(plan_analysis, user_context)
        
        plan = ExecutionPlan(
            plan_id=plan_id,
            plan_type=plan_analysis["plan_type"],
            user_message=message,
            goal=plan_analysis["goal"],
            steps=steps,
            context=plan_analysis.get("context", {}),
            total_steps=len(steps)
        )
        
        return plan
    
    def _analyze_user_request(self, message: str, user_context, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Analyze user request to determine the appropriate plan"""
        
        msg_lower = message.lower()
        context = {"previous_results": None}
        
        # Check if this is a follow-up question
        if conversation_history:
            last_response = conversation_history[-1] if conversation_history else None
            if last_response and last_response.get("role") == "assistant":
                context["previous_results"] = last_response.get("data")
        
        # Analyze question patterns
        if ("how many" in msg_lower and "failed" in msg_lower) or ("why" in msg_lower and ("fail" in msg_lower or "error" in msg_lower)):
            if context["previous_results"] or self._has_recent_filter_results(user_context.user_id):
                # Follow-up analysis on existing data
                return {
                    "plan_type": PlanType.FOLLOW_UP,
                    "goal": "Analyze failure reasons from recent data",
                    "analysis_type": "failure_analysis",
                    "context": context
                }
            else:
                # Need to fetch data first, then analyze
                return {
                    "plan_type": PlanType.ANALYSIS,
                    "goal": "Filter failed invoices and analyze failure reasons",
                    "analysis_type": "failure_analysis",
                    "context": context
                }
        
        elif "count" in msg_lower or "how many" in msg_lower:
            return {
                "plan_type": PlanType.SINGLE_TOOL,
                "goal": "Count specific items",
                "analysis_type": "count",
                "context": context
            }
        
        elif "filter" in msg_lower or "show" in msg_lower or "list" in msg_lower:
            return {
                "plan_type": PlanType.SINGLE_TOOL,
                "goal": "Filter and display data",
                "analysis_type": "filter",
                "context": context
            }
        
        elif "create" in msg_lower and "ticket" in msg_lower:
            return {
                "plan_type": PlanType.SINGLE_TOOL,
                "goal": "Create support ticket",
                "analysis_type": "ticket_creation",
                "context": context
            }
        
        elif "export" in msg_lower or "download" in msg_lower:
            return {
                "plan_type": PlanType.SINGLE_TOOL,
                "goal": "Export data to file",
                "analysis_type": "export",
                "context": context
            }
        
        else:
            return {
                "plan_type": PlanType.SINGLE_TOOL,
                "goal": "Handle general request",
                "analysis_type": "general",
                "context": context
            }
    
    def _has_recent_filter_results(self, user_id: str) -> bool:
        """Check if user has recent filter results that can be analyzed"""
        try:
            from database.connection import db_manager
            
            # Check for recent filter_data tool executions
            recent_trace = db_manager.execute_query("""
                SELECT tool_calls, results FROM traces 
                WHERE user_id = ? AND tool_calls LIKE '%filter_data%'
                ORDER BY timestamp DESC LIMIT 1
            """, (user_id,), fetch_one=True)
            
            if recent_trace:
                # Check if it was within last 10 minutes
                import datetime
                trace_time = db_manager.execute_query("""
                    SELECT timestamp FROM traces 
                    WHERE user_id = ? AND tool_calls LIKE '%filter_data%'
                    ORDER BY timestamp DESC LIMIT 1
                """, (user_id,), fetch_one=True)
                
                if trace_time:
                    trace_timestamp = datetime.datetime.fromisoformat(trace_time['timestamp'])
                    time_diff = datetime.datetime.now() - trace_timestamp
                    return time_diff.total_seconds() < 600  # 10 minutes
            
            return False
        except:
            return False
    
    def _create_plan_steps(self, plan_analysis: Dict[str, Any], user_context) -> List[PlanStep]:
        """Create detailed plan steps based on analysis"""
        
        steps = []
        plan_type = plan_analysis["plan_type"]
        analysis_type = plan_analysis.get("analysis_type")
        context = plan_analysis.get("context", {})
        
        if plan_type == PlanType.FOLLOW_UP and analysis_type == "failure_analysis":
            # Analyze existing data without re-fetching
            step = PlanStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                description="Analyze failure reasons from recent filter results",
                tool_name="analyze_data",
                parameters={"analysis_type": "failure_reasons", "use_recent_data": True},
                reasoning="User is asking for analysis of already filtered data"
            )
            steps.append(step)
            
        elif plan_type == PlanType.ANALYSIS and analysis_type == "failure_analysis":
            # Two-step process: filter then analyze
            step1 = PlanStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                description="Filter failed invoices",
                tool_name="filter_data",
                parameters={"dataset": "invoices", "status": "failed"},
                reasoning="First, get all failed invoices to analyze"
            )
            steps.append(step1)
            
            step2 = PlanStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=2,
                description="Analyze failure reasons",
                tool_name="analyze_data",
                parameters={"analysis_type": "failure_reasons", "source_step": step1.step_id},
                reasoning="Analyze the failure patterns and reasons",
                depends_on=[step1.step_id]
            )
            steps.append(step2)
            
        elif plan_type == PlanType.SINGLE_TOOL:
            # Single tool execution with smart parameter detection
            tool_name, parameters = self._detect_tool_and_parameters(plan_analysis, user_context)
            
            step = PlanStep(
                step_id=f"step_{uuid.uuid4().hex[:8]}",
                step_number=1,
                description=f"Execute {tool_name} with specified parameters",
                tool_name=tool_name,
                parameters=parameters,
                reasoning=f"Single step execution for {analysis_type}"
            )
            steps.append(step)
        
        return steps
    
    def _detect_tool_and_parameters(self, plan_analysis: Dict[str, Any], user_context) -> tuple[str, Dict[str, Any]]:
        """Detect the appropriate tool and parameters for single-step plans"""
        
        analysis_type = plan_analysis.get("analysis_type")
        message = plan_analysis.get("user_message", "").lower()
        
        if analysis_type == "filter" or "filter" in message:
            params = {"dataset": "invoices"}
            
            # Smart parameter detection
            if "failed" in message:
                params["status"] = "failed"
            elif "pending" in message:
                params["status"] = "pending"
            elif "processed" in message:
                params["status"] = "processed"
            
            if "indisky" in message:
                params["vendor"] = "IndiSky"
            elif "techsolutions" in message:
                params["vendor"] = "TechSolutions"
            
            if "last month" in message:
                params["period"] = "last month"
            elif "last week" in message:
                params["period"] = "last week"
            elif "today" in message:
                params["period"] = "today"
            
            return "filter_data", params
            
        elif analysis_type == "export":
            params = {"dataset": "invoices", "format": "csv"}
            
            # Copy filter parameters for export
            if "failed" in message:
                params["status"] = "failed"
            if "indisky" in message:
                params["vendor"] = "IndiSky"
            if "last month" in message:
                params["period"] = "last month"
            
            return "export_report", params
            
        elif analysis_type == "ticket_creation":
            # Extract title from message
            title = message.replace("create ticket", "").replace("for", "").strip()
            if not title:
                title = "Support request"
            
            params = {
                "title": title,
                "description": plan_analysis.get("user_message", "")
            }
            
            return "create_ticket", params
            
        elif analysis_type == "count":
            params = {"dataset": "invoices"}
            
            if "failed" in message:
                params["status"] = "failed"
            
            return "filter_data", params
        
        else:
            # Default to filter_data
            return "filter_data", {"dataset": "invoices"}
    
    def execute_plan(self, plan: ExecutionPlan, user_context, trace_id: str = None) -> Dict[str, Any]:
        """Execute the plan with detailed tracing"""
        
        plan.start_time = time.time()
        execution_results = []
        step_data_store = {}  # Store data from each step for dependent steps
        
        print(f"\n🎯 **Executing Plan**: {plan.goal}")
        print(f"📋 **Total Steps**: {plan.total_steps}")
        
        for step in plan.steps:
            # Check dependencies
            if step.depends_on:
                missing_deps = [dep for dep in step.depends_on if dep not in step_data_store]
                if missing_deps:
                    step.status = PlanStepStatus.SKIPPED
                    step.error_message = f"Missing dependencies: {missing_deps}"
                    continue
            
            # Execute step
            step.status = PlanStepStatus.RUNNING
            step_start_time = time.time()
            
            print(f"\n🔧 **Step {step.step_number}**: {step.description}")
            print(f"💭 **Reasoning**: {step.reasoning}")
            print(f"🛠️ **Tool**: {step.tool_name}")
            print(f"⚙️ **Parameters**: {step.parameters}")
            
            try:
                # Handle special analysis steps
                if step.tool_name == "analyze_data":
                    result = self._execute_analysis_step(step, step_data_store, user_context)
                else:
                    # Execute regular tool
                    if not self.registry:
                        # Re-initialize if needed
                        self._init_dependencies()
                    
                    if not self.registry:
                        raise Exception("Tool registry not available - cannot execute tools")
                    
                    tool_result = self.registry.execute_tool(step.tool_name, step.parameters, user_context)
                    result = {
                        "success": tool_result.status == "success",
                        "message": tool_result.message,
                        "data": tool_result.data,
                        "status": tool_result.status
                    }
                
                step.result = result
                step.execution_time_ms = int((time.time() - step_start_time) * 1000)
                
                if result["success"]:
                    step.status = PlanStepStatus.COMPLETED
                    plan.completed_steps += 1
                    
                    # Store step data for dependent steps
                    step_data_store[step.step_id] = result.get("data")
                    
                    print(f"✅ **Completed**: {result['message']}")
                else:
                    step.status = PlanStepStatus.FAILED
                    step.error_message = result["message"]
                    plan.failed_steps += 1
                    
                    print(f"❌ **Failed**: {result['message']}")
                
                # Log to trace service
                if trace_id and self.trace_service:
                    self.trace_service.add_tool_execution(
                        trace_id, step.tool_name, step.parameters, 
                        result.get("data"), result["status"], step.execution_time_ms
                    )
                
                execution_results.append({
                    "step": step.step_number,
                    "description": step.description,
                    "tool_name": step.tool_name,
                    "reasoning": step.reasoning,
                    "status": step.status,
                    "result": result,
                    "execution_time_ms": step.execution_time_ms
                })
                
            except Exception as e:
                step.status = PlanStepStatus.FAILED
                step.error_message = str(e)
                plan.failed_steps += 1
                
                print(f"❌ **Error**: {str(e)}")
                print(f"❌ **Error Type**: {type(e).__name__}")
                import traceback
                print(f"❌ **Traceback**: {traceback.format_exc()}")
                
                execution_results.append({
                    "step": step.step_number,
                    "description": step.description,
                    "tool_name": step.tool_name,
                    "reasoning": step.reasoning,
                    "status": step.status,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "execution_time_ms": int((time.time() - step_start_time) * 1000)
                })
        
        plan.end_time = time.time()
        total_time = int((plan.end_time - plan.start_time) * 1000)
        
        success = plan.completed_steps > 0 and plan.failed_steps == 0
        
        print(f"\n📊 **Plan Summary**:")
        print(f"   ✅ Completed: {plan.completed_steps}/{plan.total_steps} steps")
        print(f"   ⏱️ Total time: {total_time}ms")
        print(f"   🎯 Success: {success}")
        
        return {
            "success": success,
            "plan_id": plan.plan_id,
            "plan_type": plan.plan_type,
            "goal": plan.goal,
            "completed_steps": plan.completed_steps,
            "failed_steps": plan.failed_steps,
            "total_steps": plan.total_steps,
            "execution_time_ms": total_time,
            "results": execution_results,
            "step_data": step_data_store
        }
    
    def _execute_analysis_step(self, step: PlanStep, step_data_store: Dict[str, Any], user_context) -> Dict[str, Any]:
        """Execute analysis steps that work with data from previous steps or recent history"""
        
        analysis_type = step.parameters.get("analysis_type")
        
        if analysis_type == "failure_reasons":
            if step.parameters.get("use_recent_data"):
                # Get recent filter data from database
                data = self._get_recent_filter_data(user_context.user_id)
            else:
                # Get data from previous step
                source_step = step.parameters.get("source_step")
                data = step_data_store.get(source_step)
            
            if not data:
                return {
                    "success": False,
                    "message": "No data available for analysis",
                    "data": None,
                    "status": "error"
                }
            
            # Perform failure analysis
            analysis_result = self._analyze_failure_reasons(data)
            
            return {
                "success": True,
                "message": f"Analyzed {analysis_result['total_failed']} failed invoices",
                "data": analysis_result,
                "status": "success"
            }
        
        return {
            "success": False,
            "message": f"Unknown analysis type: {analysis_type}",
            "data": None,
            "status": "error"
        }
    
    def _get_recent_filter_data(self, user_id: str) -> Dict[str, Any]:
        """Get data from recent filter operation"""
        try:
            from database.connection import db_manager
            
            recent_trace = db_manager.execute_query("""
                SELECT results FROM traces 
                WHERE user_id = ? AND tool_calls LIKE '%filter_data%'
                ORDER BY timestamp DESC LIMIT 1
            """, (user_id,), fetch_one=True)
            
            if recent_trace and recent_trace['results']:
                results = json.loads(recent_trace['results'])
                if results:
                    # Extract the data from the first result
                    first_result = results[0] if isinstance(results, list) else results
                    return first_result.get('result', {})
            
            return None
        except Exception as e:
            print(f"Error getting recent filter data: {e}")
            return None
    
    def _analyze_failure_reasons(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze failure reasons from invoice data"""
        
        results = data.get("results", []) if data else []
        
        if not results:
            return {
                "total_failed": 0,
                "failure_reasons": {},
                "recommendations": []
            }
        
        # Analyze failure patterns
        failure_reasons = {}
        total_failed = len(results)
        
        for invoice in results:
            error_msg = invoice.get("error_message", "Unknown error")
            if error_msg and error_msg != "None" and error_msg != "":
                failure_reasons[error_msg] = failure_reasons.get(error_msg, 0) + 1
            else:
                failure_reasons["Unknown error"] = failure_reasons.get("Unknown error", 0) + 1
        
        # Generate recommendations
        recommendations = []
        
        for reason, count in failure_reasons.items():
            if "GSTIN" in reason.upper():
                recommendations.append(f"Update vendor GSTIN information for {count} invoices")
            elif "TAX" in reason.upper():
                recommendations.append(f"Review tax calculation setup for {count} invoices")
            elif "VALIDATION" in reason.upper():
                recommendations.append(f"Fix data validation issues for {count} invoices")
        
        if not recommendations:
            recommendations.append("Review error logs for detailed failure information")
        
        return {
            "total_failed": total_failed,
            "failure_reasons": failure_reasons,
            "recommendations": recommendations,
            "analysis_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

# Global planning agent instance
planning_agent = PlanningAgent()