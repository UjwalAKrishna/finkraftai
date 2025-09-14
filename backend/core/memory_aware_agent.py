# Optimized Memory-Aware Agent - Minimal LLM usage with smart caching

import json
import hashlib
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from backend.tools.base_tool import UserContext
from backend.core.tool_registry import registry
from backend.core.memory_manager import memory_manager
from backend.services.trace_service import trace_service
from backend.core.llm_provider import llm_manager
from database.connection import db_manager

class MemoryAwareAgent:
    """Optimized agent with minimal LLM usage and smart response patterns"""
    
    def __init__(self):
        self.llm = llm_manager
        self.llm_available = self.llm.is_any_provider_available()
        self.response_cache = {}  # Simple response cache
        self.pattern_responses = {
            'greetings': ['hi', 'hello', 'hey', 'good morning'],
            'help': ['help', 'what can you do', 'commands'],
            'thanks': ['thank you', 'thanks', 'appreciate'],
        }
        
    def process_message(self, message: str, user_context: UserContext, 
                       session_id: str = None) -> Dict[str, Any]:
        """Process message with enhanced planning and execution"""
        
        try:
            # Check simple patterns first (NO LLM call)
            pattern_response = self._check_patterns(message)
            if pattern_response:
                self._store_simple_conversation(user_context.user_id, message, pattern_response)
                return {'success': True, 'message': pattern_response, 'tool_used': None, 'cached': True}
            
            # Check cache for identical requests
            cache_key = self._get_cache_key(user_context.user_id, message)
            cached = self.response_cache.get(cache_key)
            if cached and (time.time() - cached['time']) < 900:  # 15 min cache
                return cached['response']
            
            # Get conversation context for planning (PRD: "Don't make me repeat myself")
            thread_id = memory_manager.get_active_thread(user_context.user_id, session_id)
            conversation_context = memory_manager.get_conversation_context(user_context.user_id, message, thread_id)
            recent_msgs = conversation_context.get('recent_messages', [])
            
            # Store user message
            memory_manager.store_conversation(user_context.user_id, 'user', message, thread_id, session_id)
            
            # Use LLM-first AI agent approach
            trace_id = trace_service.create_execution_trace(user_context.user_id, message, workspace_id=user_context.workspace_id)
            
            # Let LLM decide what tools to use and execute them
            response_data = self._execute_llm_agent(message, user_context, recent_msgs, trace_id)
            
            # Extract the natural response text for storage and display
            if isinstance(response_data, dict):
                response_text = response_data.get('natural_response', 'Task completed.')
                trace_summary = response_data.get('trace_summary', '')
                show_traces = response_data.get('show_traces', False)
            else:
                # Fallback for backward compatibility
                response_text = str(response_data)
                trace_summary = ''
                show_traces = False
            
            # Complete trace
            trace_service.complete_trace(trace_id, response_text)
            
            # Store response with tool context for memory (PRD: conversation continuity)
            tool_context = {
                'tools_used': response_data.get('tool_used', ''),
                'suggestions': response_data.get('suggestions', []),
                'analysis': response_data.get('analysis', ''),
                'execution_success': response_data.get('success', True)
            }
            
            memory_manager.store_conversation(
                user_context.user_id, 
                'assistant', 
                response_text, 
                thread_id, 
                session_id,
                tool_name=response_data.get('tool_used'),
                tool_result=tool_context
            )
            
            final_result = {
                'success': response_data.get('success', True),
                'message': response_text,
                'tool_used': response_data.get('tool_used', 'llm_agent'),
                'trace_id': trace_id,
                'trace_summary': trace_summary,
                'show_traces': show_traces,
                'cached': False
            }
            
            # Cache if no personal data
            if not self._has_personal_data(response_text):
                self.response_cache[cache_key] = {'response': final_result, 'time': time.time()}
            
            return final_result
            
        except Exception as e:
            print(f"Error in process_message: {e}")
            return {'success': False, 'message': f"Error: {str(e)}", 'tool_used': None}
    
    def _check_patterns(self, message: str) -> str:
        """Check for simple patterns - NO LLM call needed"""
        msg_lower = message.lower().strip()
        
        # Only match if the message is primarily a simple pattern (not part of a longer request)
        for pattern_type, patterns in self.pattern_responses.items():
            for pattern in patterns:
                # More precise matching - pattern should be the whole message or at start/end
                if (msg_lower == pattern or 
                    msg_lower.startswith(pattern + " ") or 
                    msg_lower.endswith(" " + pattern) or
                    msg_lower.startswith(pattern + "!") or
                    msg_lower.endswith("!" + pattern)):
                    
                    if pattern_type == 'greetings':
                        return "Hello! I'm FinkraftAI, your business assistant. I can help filter data, create reports, manage tickets, and answer questions."
                    elif pattern_type == 'help':
                        return "I can help you with: filtering invoices, creating reports, managing tickets, viewing data. Try saying 'filter invoices for last month' or 'create a ticket'."
                    elif pattern_type == 'thanks':
                        return "You're welcome! Let me know if you need anything else."
        return None
    
    def _get_cache_key(self, user_id: str, message: str) -> str:
        """Generate cache key for identical requests"""
        normalized = message.lower().strip()
        # Remove dates and specific names for better cache hits
        import re
        normalized = re.sub(r'\d{4}-\d{2}-\d{2}', 'DATE', normalized)
        normalized = re.sub(r'(indisky|techsolutions|global)', 'VENDOR', normalized)
        return hashlib.md5(f"{user_id}:{normalized}".encode()).hexdigest()[:12]
    
    def _get_recent_messages(self, user_id: str, limit: int = 3) -> List[Dict]:
        """Get recent conversation context"""
        try:
            from database.connection import db_manager
            messages = db_manager.execute_query("""
                SELECT role, message FROM conversations 
                WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?
            """, (user_id, limit))
            return [{'role': m[0], 'message': m[1][:100]} for m in reversed(messages)]
        except:
            return []
    
    def _store_simple_conversation(self, user_id: str, message: str, response: str):
        """Store simple conversation without full memory processing"""
        try:
            thread_id = memory_manager.get_active_thread(user_id, None)
            memory_manager.store_conversation(user_id, 'user', message, thread_id, None)
            memory_manager.store_conversation(user_id, 'assistant', response, thread_id, None)
        except:
            pass  # Continue without storage if fails
    
    def _get_llm_decision(self, message: str, user_context: UserContext, recent_msgs: List[Dict]) -> Dict[str, Any]:
        """Single optimized LLM call for decision making with fallbacks"""
        if not self.llm_available:
            return self._fallback_decision(message, user_context)
        
        # Get minimal tools info
        tools = registry.get_available_tools_info(user_context.user_id)
        tools_str = ", ".join([f"{t['name']}({t['description'][:30]})" for t in tools])
        
        # Build minimal context
        context = "\n".join([f"{m['role']}: {m['message']}" for m in recent_msgs[-2:]])
        
        prompt = f"""FinkraftAI business assistant for {user_context.user_id} ({user_context.role})

User asks: "{message}"

Available tools: {tools_str}

Examples:
- "tell vendor names" → {{"tool_call": {{"name": "filter_data", "parameters": {{"dataset": "invoices"}}}}, "reasoning": "Getting vendor information", "answer_question": "vendor_list"}}
- "how many failed invoices and why" → {{"plan": [{{"step": 1, "action": "filter_failed", "tool_call": {{"name": "filter_data", "parameters": {{"dataset": "invoices", "status": "failed"}}}}, "reasoning": "Get failed invoices to analyze"}}], "answer_question": "failed_analysis", "reasoning": "Multi-step analysis needed"}}
- "filter last month invoices" → {{"tool_call": {{"name": "filter_data", "parameters": {{"dataset": "invoices", "period": "last month"}}}}, "reasoning": "Filtering invoices"}}
- "create ticket for payment issues" → {{"tool_call": {{"name": "create_ticket", "parameters": {{"title": "payment issues", "description": "create ticket for payment issues"}}}}, "reasoning": "Creating support ticket"}}

Respond JSON EXACTLY like examples above:"""
        
        try:
            print(f"Attempting LLM call with {self.llm.get_current_provider()}")
            response = self.llm.generate_response(prompt)
            parsed = json.loads(self._extract_json(response))
            print("✓ LLM responded successfully")
            return parsed
        except Exception as e:
            print(f"LLM error ({type(e).__name__}): {str(e)[:100]}")
            print("→ Using intelligent fallback")
            return self._fallback_decision(message, user_context)
    
    def _fallback_decision(self, message: str, user_context: UserContext) -> Dict[str, Any]:
        """Fallback decision making when LLM is unavailable"""
        msg_lower = message.lower()
        
        # Handle complex questions that need analysis
        if ('how many' in msg_lower and 'failed' in msg_lower) or ('why' in msg_lower and 'fail' in msg_lower):
            # Multi-step: filter failed invoices, then analyze reasons
            return {
                "plan": [
                    {
                        "step": 1,
                        "action": "filter_failed_invoices",
                        "tool_call": {
                            "name": "filter_data",
                            "parameters": {
                                "dataset": "invoices",
                                "status": "failed"
                            }
                        },
                        "reasoning": "First, get all failed invoices to analyze"
                    }
                ],
                "answer_question": "failed_analysis",
                "reasoning": "Multi-step analysis: filter failed invoices and analyze failure reasons"
            }
        
        # Handle direct questions about vendors
        elif 'vendor' in msg_lower and ('all' in msg_lower or 'list' in msg_lower or 'tell' in msg_lower or 'names' in msg_lower):
            return {
                "tool_call": {
                    "name": "filter_data",
                    "parameters": {
                        "dataset": "invoices"
                    }
                },
                "reasoning": "Getting vendor information",
                "answer_question": "vendor_list"
            }
        
        # Check for specific questions that need answers
        elif 'how many' in msg_lower or 'count' in msg_lower or 'list' in msg_lower:
            if 'failed' in msg_lower and 'invoice' in msg_lower:
                return {
                    "tool_call": {
                        "name": "filter_data",
                        "parameters": {
                            "dataset": "invoices",
                            "status": "failed"
                        }
                    },
                    "reasoning": "Getting failed invoices count",
                    "answer_question": "failed_invoice_count"
                }
            elif 'invoice' in msg_lower:
                return {
                    "tool_call": {
                        "name": "filter_data",
                        "parameters": {
                            "dataset": "invoices"
                        }
                    },
                    "reasoning": "Getting all invoices",
                    "answer_question": "invoice_list"
                }
        
        # Simple keyword-based tool selection
        elif 'filter' in msg_lower and ('invoice' in msg_lower or 'data' in msg_lower):
            params = {"dataset": "invoices"}
            if 'failed' in msg_lower:
                params['status'] = 'failed'
            if 'pending' in msg_lower:
                params['status'] = 'pending'
            if 'indisky' in msg_lower:
                params['vendor'] = 'IndiSky'
            
            # Add time period detection
            if 'last month' in msg_lower:
                params['period'] = 'last month'
            elif 'last week' in msg_lower:
                params['period'] = 'last week'
            elif 'today' in msg_lower:
                params['period'] = 'today'
            
            return {
                "tool_call": {
                    "name": "filter_data", 
                    "parameters": params
                },
                "reasoning": "Filtering invoices with specified criteria"
            }
        
        elif 'create' in msg_lower and 'ticket' in msg_lower:
            # Extract meaningful title from message
            if 'for' in msg_lower:
                # Extract what comes after "for" as title
                parts = message.split(' for ', 1)
                if len(parts) > 1:
                    title = parts[1].strip()
                else:
                    title = message.strip()
            else:
                title = message.strip()
            
            # Ensure title is not empty and not too long
            if not title:
                title = "Support ticket"
            elif len(title) > 100:
                title = title[:97] + "..."
            
            return {
                "tool_call": {
                    "name": "create_ticket",
                    "parameters": {
                        "title": title,
                        "description": message
                    }
                },
                "reasoning": "Creating support ticket"
            }
        
        elif 'export' in msg_lower or 'download' in msg_lower:
            params = {
                "dataset": "invoices",
                "format": "csv"
            }
            
            # Parse filters from export request
            if 'failed' in msg_lower:
                params['status'] = 'failed'
            if 'pending' in msg_lower:
                params['status'] = 'pending'
            if 'indisky' in msg_lower:
                params['vendor'] = 'IndiSky'
            
            # Parse time periods
            if 'last month' in msg_lower:
                params['period'] = 'last month'
            elif 'last week' in msg_lower:
                params['period'] = 'last week'
            elif 'today' in msg_lower:
                params['period'] = 'today'
            
            return {
                "tool_call": {
                    "name": "export_report",
                    "parameters": params
                },
                "reasoning": "Exporting filtered data with specified criteria"
            }
        
        elif 'ticket' in msg_lower and ('show' in msg_lower or 'view' in msg_lower):
            return {
                "tool_call": {
                    "name": "view_tickets",
                    "parameters": {}
                },
                "reasoning": "Detected view tickets request"
            }
        
        else:
            return {
                "response": f"I understand you want help with: {message}. I can help with filtering data, creating tickets, exporting reports, and viewing tickets. Try being more specific like 'filter failed invoices' or 'create a ticket for missing GSTIN'.",
                "reasoning": "No specific tool needed"
            }
    
    def _execute_single_tool(self, tool_call: Dict, user_context: UserContext, trace_id: str = None) -> Dict[str, Any]:
        """Execute a single tool and return result"""
        tool_name = tool_call['name']
        parameters = tool_call.get('parameters', {})
        
        try:
            if trace_id:
                trace_service.add_tool_execution(trace_id, tool_name, parameters, None, 'running', 0)
            
            result = registry.execute_tool(tool_name, parameters, user_context)
            
            if trace_id:
                trace_service.add_tool_execution(trace_id, tool_name, parameters, result.data, result.status, 0)
            
            return {
                'success': result.status == 'success',
                'tool_name': tool_name,
                'parameters': parameters,
                'message': result.message,
                'data': result.data,
                'status': result.status
            }
        except Exception as e:
            if trace_id:
                trace_service.add_tool_execution(trace_id, tool_name, parameters, None, 'error', 0)
            
            return {
                'success': False,
                'tool_name': tool_name,
                'parameters': parameters,
                'message': f"Tool execution failed: {str(e)}",
                'data': None,
                'status': 'error'
            }
    
    def _execute_plan(self, decision: Dict, user_context: UserContext, trace_id: str) -> Dict[str, Any]:
        """Execute a multi-step plan"""
        plan = decision['plan']
        all_results = []
        
        trace_service.update_trace_plan(trace_id, f"Executing {len(plan)} step plan")
        
        for step_info in plan:
            step_num = step_info['step']
            tool_call = step_info['tool_call']
            reasoning = step_info['reasoning']
            
            print(f"🔧 Step {step_num}: {reasoning}")
            
            # Execute the step
            result = self._execute_single_tool(tool_call, user_context, trace_id)
            all_results.append({
                **result,
                'step': step_num,
                'reasoning': reasoning,
                'action': step_info.get('action', tool_call['name'])
            })
            
            # If step fails, stop plan execution
            if not result['success']:
                print(f"❌ Step {step_num} failed: {result['message']}")
                break
            else:
                print(f"✅ Step {step_num} completed: {result['message']}")
        
        success = all(r['success'] for r in all_results)
        
        return {
            'success': success,
            'plan_results': all_results,
            'completed_steps': len([r for r in all_results if r['success']]),
            'total_steps': len(plan)
        }
    
    def _execute_tools(self, decision: Dict, user_context: UserContext, message: str) -> Dict[str, Any]:
        """Execute tools based on LLM decision"""
        tool_calls = decision.get('tool_calls', [])
        if not tool_calls and decision.get('tool_call'):
            tool_calls = [decision['tool_call']]
        
        if not tool_calls:
            return {'success': True, 'tool_used': None}
        
        results = []
        for tool_call in tool_calls:
            try:
                result = registry.execute_tool(tool_call['name'], tool_call.get('parameters', {}), user_context)
                results.append({
                    'success': result.status == 'success',
                    'tool_name': tool_call['name'],
                    'message': result.message,
                    'data': result.data
                })
            except Exception as e:
                results.append({
                    'success': False,
                    'tool_name': tool_call.get('name', 'unknown'),
                    'message': str(e),
                    'data': None
                })
        
        # Return summary result
        success = all(r['success'] for r in results)
        tool_used = results[0]['tool_name'] if len(results) == 1 else 'multi_step'
        
        return {'success': success, 'tool_used': tool_used, 'results': results}
    
    def _build_tool_response(self, message: str, result: Dict, explanation: str) -> str:
        """Build intelligent response that answers user questions"""
        if not result.get('results'):
            return "I completed your request."
        
        # Get the decision context to understand what user was asking
        decision_context = getattr(self, '_last_decision_context', {})
        answer_type = decision_context.get('answer_question')
        
        responses = []
        
        # Generate specific answers based on user question
        for r in result['results']:
            if r['success']:
                tool_data = r.get('data', {})
                
                # Answer specific questions about data
                if answer_type == 'vendor_list' and tool_data:
                    # Extract unique vendor names from invoice data
                    results = tool_data.get('results', [])
                    if results:
                        vendors = set()
                        for invoice in results:
                            vendor_name = invoice.get('vendor_name')
                            if vendor_name:
                                vendors.add(vendor_name)
                        
                        vendor_list = sorted(list(vendors))
                        if vendor_list:
                            responses.append(f"Here are all the vendor names ({len(vendor_list)} vendors):")
                            responses.append("• " + "\n• ".join(vendor_list))
                        else:
                            responses.append("No vendor information found in the invoices.")
                    else:
                        responses.append("No invoice data available to extract vendor names.")
                
                elif answer_type == 'failed_invoice_count' and tool_data:
                    failed_count = tool_data.get('filtered_records', 0)
                    total_count = tool_data.get('total_records', 0)
                    responses.append(f"There are **{failed_count} failed invoices** out of {total_count} total invoices.")
                    
                    # Add details if available
                    if failed_count > 0:
                        responses.append(f"These invoices have processing errors and need attention.")
                
                elif answer_type == 'failed_analysis' and tool_data:
                    # Analyze failed invoices and their reasons
                    results = tool_data.get('results', [])
                    failed_count = len(results)
                    
                    if failed_count > 0:
                        responses.append(f"Found **{failed_count} failed invoices**. Here's the analysis:")
                        
                        # Analyze failure reasons
                        failure_reasons = {}
                        for invoice in results:
                            error_msg = invoice.get('error_message', 'Unknown error')
                            if error_msg and error_msg != 'None':
                                failure_reasons[error_msg] = failure_reasons.get(error_msg, 0) + 1
                        
                        if failure_reasons:
                            responses.append("\n**Failure reasons:**")
                            for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                                responses.append(f"• **{count} invoices**: {reason}")
                        else:
                            responses.append("• No specific error messages found in the failed invoices.")
                        
                        # Add recommendations
                        if 'GSTIN' in str(failure_reasons):
                            responses.append("\n💡 **Recommendation**: Update vendor GSTIN information to resolve these failures.")
                    else:
                        responses.append("No failed invoices found.")
                
                elif answer_type == 'invoice_list' and tool_data:
                    total_count = tool_data.get('total_records', 0)
                    showing = tool_data.get('filtered_records', 0)
                    responses.append(f"You have **{total_count} total invoices** in the system.")
                    if showing < total_count:
                        responses.append(f"Showing {showing} most recent invoices.")
                
                elif 'filter' in message.lower():
                    # For filter requests, provide clear summary
                    if tool_data:
                        filtered = tool_data.get('filtered_records', 0)
                        total = tool_data.get('total_records', 0)
                        filters = tool_data.get('filters_applied', {})
                        
                        filter_desc = []
                        if filters.get('status'):
                            filter_desc.append(f"status: {filters['status']}")
                        if filters.get('vendor'):
                            filter_desc.append(f"vendor: {filters['vendor']}")
                        if filters.get('period'):
                            filter_desc.append(f"period: {filters['period']}")
                        
                        if filter_desc:
                            responses.append(f"Found **{filtered} invoices** matching your filters ({', '.join(filter_desc)}).")
                        else:
                            responses.append(f"Found **{filtered} invoices** from {total} total.")
                    else:
                        responses.append(r['message'])
                else:
                    responses.append(r['message'])
            else:
                responses.append(f"Error: {r['message']}")
        
        # Add explanation if provided
        if explanation and not any(explanation in resp for resp in responses):
            responses.insert(0, explanation)
        
        return " ".join(responses) if responses else "Task completed."
    
    def _build_plan_response(self, message: str, result: Dict, decision: Dict) -> str:
        """Build response for plan execution"""
        plan_results = result.get('plan_results', [])
        completed_steps = result.get('completed_steps', 0)
        total_steps = result.get('total_steps', 0)
        answer_type = decision.get('answer_question')
        
        if not plan_results:
            return "Plan execution completed."
        
        # Build response based on the plan execution
        responses = []
        
        # Show plan execution summary
        if result['success']:
            responses.append(f"✅ **Plan completed** ({completed_steps}/{total_steps} steps):")
        else:
            responses.append(f"⚠️ **Plan partially completed** ({completed_steps}/{total_steps} steps):")
        
        # Show each step
        for step_result in plan_results:
            step_num = step_result['step']
            reasoning = step_result['reasoning']
            success = step_result['success']
            status_icon = "✅" if success else "❌"
            
            responses.append(f"\n{status_icon} **Step {step_num}**: {reasoning}")
            if not success:
                responses.append(f"   Error: {step_result['message']}")
        
        # Add analysis for failed_analysis questions
        if answer_type == 'failed_analysis' and plan_results:
            # Get data from the first (filter) step
            filter_result = plan_results[0]
            if filter_result['success'] and filter_result['data']:
                tool_data = filter_result['data']
                results = tool_data.get('results', [])
                failed_count = len(results)
                
                if failed_count > 0:
                    responses.append(f"\n📊 **Analysis Results:**")
                    responses.append(f"Found **{failed_count} failed invoices**")
                    
                    # Analyze failure reasons
                    failure_reasons = {}
                    for invoice in results:
                        error_msg = invoice.get('error_message', 'Unknown error')
                        if error_msg and error_msg != 'None' and error_msg != '':
                            failure_reasons[error_msg] = failure_reasons.get(error_msg, 0) + 1
                    
                    if failure_reasons:
                        responses.append("\n**Why they failed:**")
                        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                            responses.append(f"• **{count} invoices**: {reason}")
                        
                        # Add smart recommendations
                        if 'GSTIN' in str(failure_reasons).upper():
                            responses.append("\n💡 **Recommendation**: Contact vendors to provide missing GSTIN information")
                        elif 'TAX' in str(failure_reasons).upper():
                            responses.append("\n💡 **Recommendation**: Review tax calculation setup")
                    else:
                        responses.append("• No specific error messages available")
                else:
                    responses.append("\n📊 **Good news**: No failed invoices found!")
        
        return " ".join(responses)
    
    def _execute_llm_agent(self, message: str, user_context, recent_msgs: list, trace_id: str) -> Dict[str, Any]:
        """LLM-first AI agent that decides what tools to use and crafts responses"""
        
        try:
            # Get available tools for LLM
            available_tools = self._get_available_tools_description(user_context)
            
            # Build context for LLM
            context = self._build_agent_context(message, recent_msgs, available_tools)
            
            # Let LLM decide what to do
            llm_decision = self._get_llm_agent_decision(context, message)
            
            # Execute tools if needed
            tool_results = []
            tools_used = []
            
            if llm_decision.get('tools_to_use'):
                tools_to_use = llm_decision['tools_to_use']
                
                # Handle both list of dicts and list of strings
                if isinstance(tools_to_use, list):
                    for tool_call in tools_to_use:
                        if isinstance(tool_call, dict):
                            tool_name = tool_call.get('tool')
                            parameters = tool_call.get('parameters', {})
                        elif isinstance(tool_call, str):
                            tool_name = tool_call
                            parameters = self._get_default_parameters(tool_name, message)
                        else:
                            continue
                    
                        print(f"🔧 Executing tool: {tool_name} with {parameters}")
                        
                        # Execute the tool
                        from backend.core.tool_registry import registry
                        result = registry.execute_tool(tool_name, parameters, user_context)
                        
                        tool_results.append({
                            'tool': tool_name,
                            'parameters': parameters,
                            'result': result.data,
                            'status': result.status,
                            'message': result.message
                        })
                        tools_used.append(tool_name)
                        
                        # Log to trace
                        trace_service.add_tool_execution(trace_id, tool_name, parameters, result.data, result.status)
            
            # Let LLM craft final response using tool results
            final_response = self._get_llm_final_response(message, tool_results, llm_decision)
            
            # Get suggestions from LLM decision
            suggestions = llm_decision.get('suggestions', [])
            
            # Complete trace
            trace_service.complete_trace(trace_id, final_response)
            
            return {
                'success': True,
                'natural_response': final_response,
                'tool_used': ', '.join(tools_used) if tools_used else 'llm_only',
                'tools_executed': len(tool_results),
                'suggestions': suggestions,
                'analysis': llm_decision.get('analysis', ''),
                'trace_summary': self._build_trace_summary(tool_results, final_response),
                'show_traces': len(tool_results) > 0
            }
            
        except Exception as e:
            print(f"Error in LLM agent execution: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'natural_response': f"I encountered an error: {str(e)}",
                'tool_used': 'error',
                'tools_executed': 0,
                'suggestions': [],
                'analysis': f"Error: {str(e)}",
                'trace_summary': f"Error: {str(e)}",
                'show_traces': False
            }
    
    def _get_available_tools_description(self, user_context) -> str:
        """Get description of available tools for LLM"""
        
        tools_desc = []
        
        # Check user permissions and describe available tools
        user_permissions = user_context.get_permissions() if hasattr(user_context, 'get_permissions') else []
        
        if 'filter_data' in [p.tool_name for p in user_permissions] or True:  # Fallback for demo
            tools_desc.append("filter_data: Search and filter invoices, sales, transactions by various criteria (vendor, date, status, etc.)")
        
        if 'create_ticket' in [p.tool_name for p in user_permissions] or True:
            tools_desc.append("create_ticket: Create support tickets for issues or requests")
        
        if 'export_report' in [p.tool_name for p in user_permissions] or True:
            tools_desc.append("export_report: Export filtered data to CSV/Excel files")
        
        if 'view_tickets' in [p.tool_name for p in user_permissions] or True:
            tools_desc.append("view_tickets: View existing support tickets and their status")
        
        if 'update_ticket' in [p.tool_name for p in user_permissions] or True:
            tools_desc.append("update_ticket: Update support ticket status or add comments")
        
        return "\n".join(tools_desc)
    
    def _build_agent_context(self, message: str, recent_msgs: list, available_tools: str) -> str:
        """Build context for LLM agent decision making with conversation memory"""
        
        context_parts = []
        
        # Add conversation history with tool context (PRD: "Don't make me repeat myself")
        if recent_msgs:
            context_parts.append("Recent conversation history:")
            for msg in recent_msgs[-5:]:  # Last 5 messages for better context
                role = msg.get('role', 'unknown')
                content = msg.get('message', '')[:150]  # Truncate but keep meaningful content
                tool_used = msg.get('tool_name')
                
                if tool_used:
                    context_parts.append(f"{role}: {content} [used: {tool_used}]")
                else:
                    context_parts.append(f"{role}: {content}")
        
        # Add context awareness for follow-up questions
        if recent_msgs and len(recent_msgs) > 0:
            last_msg = recent_msgs[0]  # Most recent (DESC order)
            if last_msg.get('tool_name') == 'filter_data':
                context_parts.append("\nIMPORTANT: User just filtered data - if they ask 'why did they fail?' or similar, analyze those specific results.")
            elif last_msg.get('tool_name') == 'create_ticket':
                context_parts.append("\nIMPORTANT: User just created a ticket - offer to view tickets or update status.")
        
        context_parts.append(f"\nAvailable tools:\n{available_tools}")
        context_parts.append(f"\nCurrent user request: {message}")
        
        return "\n".join(context_parts)
    
    def _get_llm_agent_decision(self, context: str, message: str) -> Dict[str, Any]:
        """Get LLM decision on what tools to use"""
        
        prompt = f"""You are FinkraftAI, a conversational business assistant with memory and context awareness.

{context}

TASK: Analyze the user's request considering conversation history and decide what tools to use.

KEY BEHAVIORS:
1. Remember previous conversations - if user says "why did they fail?" after filtering, analyze those filtered results
2. Suggest next actions based on context - if showing failed invoices, offer to create tickets
3. Use tools for ANY data requests - invoices, tickets, sales, transactions, reports
4. For follow-up questions, consider what data was just shown

RESPONSE FORMAT (JSON only):
{{"analysis": "brief analysis", "tools_to_use": [{{"tool": "tool_name", "parameters": {{"key": "value"}}}}], "reasoning": "why chosen", "suggestions": ["next action 1", "next action 2"]}}

AVAILABLE TOOLS:
- filter_data: {{"dataset": "invoices|sales|transactions", "status": "failed|pending|processed", "vendor": "name", "period": "last month|last week|today"}}
- view_tickets: {{}} 
- create_ticket: {{"title": "title", "description": "description"}}
- export_report: {{"dataset": "invoices", "format": "csv|excel"}}
- update_ticket: {{"ticket_id": "id", "status": "open|closed"}}

EXAMPLES:
"filter invoices last month" → {{"analysis": "Get last month invoices", "tools_to_use": [{{"tool": "filter_data", "parameters": {{"dataset": "invoices", "period": "last month"}}}}], "reasoning": "User needs invoice data", "suggestions": ["Check for failed invoices", "Export to Excel"]}}

"why did they fail?" (after showing failed invoices) → {{"analysis": "Explain failures from recent data", "tools_to_use": [{{"tool": "filter_data", "parameters": {{"dataset": "invoices", "status": "failed"}}}}], "reasoning": "Need failure details to explain", "suggestions": ["Create ticket for failures", "Contact vendors"]}}

"show my tickets" → {{"analysis": "View user tickets", "tools_to_use": [{{"tool": "view_tickets", "parameters": {{}}}}], "reasoning": "User wants ticket status", "suggestions": ["Update ticket status", "Create new ticket"]}}

Return ONLY JSON:"""
        
        try:
            response = self.llm.generate_response(prompt)
            print(f"🤖 LLM Raw Response: {response}")
            
            # Try to parse JSON response
            import json
            import re
            
            # Extract JSON from response if it's wrapped in other text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                decision = json.loads(json_str)
                print(f"🎯 LLM Decision: {decision}")
                
                # Ensure suggestions are always provided for PRD compliance
                if 'suggestions' not in decision or not decision['suggestions']:
                    decision['suggestions'] = self._generate_smart_suggestions(message, decision.get('tools_to_use', []))
                    print(f"🧠 Added smart suggestions: {decision['suggestions']}")
                
                return decision
            else:
                print(f"❌ No JSON found in response: {response}")
                # Force tool usage for data requests with smart suggestions
                if any(word in prompt.lower() for word in ['filter', 'invoice', 'data', 'how many', 'vendor']):
                    print(f"🔧 Forcing tool usage for data request")
                    fallback_decision = {
                        "analysis": "Data request detected",
                        "tools_to_use": [{"tool": "filter_data", "parameters": {"dataset": "invoices", "period": "last month"}}],
                        "reasoning": "Fallback: detected data request",
                        "suggestions": self._generate_smart_suggestions(message, [{"tool": "filter_data"}])
                    }
                    return fallback_decision
                return {
                    "analysis": "Need to parse user request",
                    "tools_to_use": [],
                    "reasoning": "Could not parse LLM decision properly"
                }
        except Exception as e:
            print(f"❌ Error getting LLM decision: {e}")
            import traceback
            traceback.print_exc()
            
            # FALLBACK: Smart pattern-based decision when LLM fails (for PRD testing)
            return self._get_fallback_decision(message, context)
    
    def _get_llm_final_response(self, message: str, tool_results: list, llm_decision: Dict) -> str:
        """Get LLM's final response using tool results"""
        
        if not tool_results:
            # No tools used - direct response
            prompt = f"""You are FinkraftAI, a helpful business assistant. 

User asked: "{message}"

Since no tools were needed, provide a direct, helpful response. Be conversational and professional.

Response:"""
        else:
            # Tools were used - craft response based on results
            tools_summary = []
            for result in tool_results:
                tools_summary.append(f"Tool {result['tool']}: {result['status']} - {result.get('message', 'No message')}")
                if result.get('result'):
                    if isinstance(result['result'], dict):
                        if result['result'].get('filtered_records') is not None:
                            tools_summary.append(f"  Found {result['result']['filtered_records']} records")
                        if result['result'].get('failure_reasons'):
                            tools_summary.append(f"  Failures: {result['result']['failure_reasons']}")
            
            prompt = f"""You are FinkraftAI, a helpful business assistant.

User asked: "{message}"

I executed these tools:
{chr(10).join(tools_summary)}

Based on these results, craft a natural, conversational response that:
1. Directly answers the user's question
2. Uses the data from the tools
3. Is helpful and actionable
4. Sounds natural, not robotic

Response:"""
        
        try:
            response = self.llm.generate_response(prompt)
            return response.strip()
        except Exception as e:
            return f"I completed your request. Tool results: {len(tool_results)} tools executed."
    
    def _build_trace_summary(self, tool_results: list, final_response: str) -> str:
        """Build trace summary for optional viewing"""
        
        if not tool_results:
            return f"Direct response (no tools used): {final_response[:100]}..."
        
        summary_parts = [f"Executed {len(tool_results)} tools:"]
        for result in tool_results:
            summary_parts.append(f"• {result['tool']} - {result['status']}")
        
        summary_parts.append(f"Generated response: {final_response[:100]}...")
        return "\n".join(summary_parts)
    
    def _get_default_parameters(self, tool_name: str, message: str) -> Dict[str, Any]:
        """Get default parameters for a tool based on the user message"""
        msg_lower = message.lower()
        
        if tool_name == "filter_data":
            params = {"dataset": "invoices"}
            
            # Smart parameter detection from message
            if "failed" in msg_lower:
                params["status"] = "failed"
            elif "pending" in msg_lower:
                params["status"] = "pending"
            elif "processed" in msg_lower:
                params["status"] = "processed"
                
            if "indisky" in msg_lower:
                params["vendor"] = "IndiSky"
            elif "techsolutions" in msg_lower:
                params["vendor"] = "TechSolutions"
                
            if "last month" in msg_lower:
                params["period"] = "last month"
            elif "last week" in msg_lower:
                params["period"] = "last week"
            elif "today" in msg_lower:
                params["period"] = "today"
                
            return params
            
        elif tool_name == "view_tickets":
            return {}
            
        elif tool_name == "create_ticket":
            # Extract title from message
            title = msg_lower.replace("create ticket", "").replace("for", "").strip()
            if not title:
                title = "Support request from chat"
            return {"title": title, "description": message}
            
        elif tool_name == "export_report":
            return {"dataset": "invoices", "format": "csv"}
            
        else:
            return {}
    
    def _generate_smart_suggestions(self, message: str, tools_used: list) -> list:
        """Generate smart suggestions based on context (PRD requirement: Don't make me repeat myself)"""
        
        suggestions = []
        msg_lower = message.lower()
        
        # Context-aware suggestions based on what tools were used
        tool_names = [tool.get('tool') if isinstance(tool, dict) else tool for tool in tools_used]
        
        if 'filter_data' in tool_names:
            if 'failed' in msg_lower:
                suggestions.extend([
                    "Why did these fail?",
                    "Create a ticket for these failures",
                    "Export failed invoices to Excel"
                ])
            elif 'invoice' in msg_lower:
                suggestions.extend([
                    "Show only failed invoices",
                    "Export this data to Excel", 
                    "Create a ticket for investigation"
                ])
            else:
                suggestions.extend([
                    "Filter by status",
                    "Export to Excel",
                    "Show summary statistics"
                ])
        
        if 'view_tickets' in tool_names:
            suggestions.extend([
                "Create a new ticket",
                "Show only open tickets",
                "Update ticket status"
            ])
        
        if 'create_ticket' in tool_names:
            suggestions.extend([
                "View all my tickets",
                "Set ticket priority",
                "Add ticket comment"
            ])
        
        # General suggestions based on message content
        if 'fail' in msg_lower and 'create' not in msg_lower:
            suggestions.append("Create a ticket for this issue")
        
        if any(word in msg_lower for word in ['vendor', 'indisky', 'techsolutions']):
            suggestions.append("Contact vendor about this")
        
        if 'export' not in msg_lower and 'download' not in msg_lower:
            suggestions.append("Download this data")
        
        # Remove duplicates and limit to 3 most relevant
        unique_suggestions = list(dict.fromkeys(suggestions))
        return unique_suggestions[:3]
    
    def _get_fallback_decision(self, message: str, context: str) -> Dict[str, Any]:
        """Fallback decision when LLM fails - smart pattern matching for PRD compliance"""
        
        msg_lower = message.lower()
        
        # Context-aware analysis for follow-up questions (PRD: "Don't make me repeat myself")
        if "why" in msg_lower and ("fail" in msg_lower or "error" in msg_lower):
            # Check if there's recent filter_data context
            if "filter_data" in context:
                return {
                    "analysis": "User asking why previous filter results failed",
                    "tools_to_use": [{"tool": "filter_data", "parameters": {"dataset": "invoices", "status": "failed"}}],
                    "reasoning": "User has context from previous filter, analyzing failure reasons",
                    "suggestions": ["Create a ticket for these failures", "Export failed invoices", "Contact vendors"]
                }
        
        # Filter requests
        if "filter" in msg_lower and "invoice" in msg_lower:
            params = {"dataset": "invoices"}
            
            if "failed" in msg_lower:
                params["status"] = "failed"
            if "indisky" in msg_lower:
                params["vendor"] = "IndiSky"
            if "last month" in msg_lower:
                params["period"] = "last month"
            
            return {
                "analysis": "User wants to filter invoice data",
                "tools_to_use": [{"tool": "filter_data", "parameters": params}],
                "reasoning": "Direct filter request detected",
                "suggestions": ["Why did these fail?", "Export to Excel", "Create a ticket"]
            }
        
        # Ticket operations
        if "ticket" in msg_lower:
            if "create" in msg_lower:
                return {
                    "analysis": "User wants to create a support ticket",
                    "tools_to_use": [{"tool": "create_ticket", "parameters": {"title": "Support request", "description": message}}],
                    "reasoning": "Ticket creation request",
                    "suggestions": ["View all tickets", "Set priority", "Add more details"]
                }
            elif "show" in msg_lower or "view" in msg_lower:
                return {
                    "analysis": "User wants to view tickets",
                    "tools_to_use": [{"tool": "view_tickets", "parameters": {}}],
                    "reasoning": "Ticket viewing request",
                    "suggestions": ["Create new ticket", "Update status", "Export ticket list"]
                }
        
        # Export requests
        if "export" in msg_lower or "download" in msg_lower:
            return {
                "analysis": "User wants to export data",
                "tools_to_use": [{"tool": "export_report", "parameters": {"dataset": "invoices", "format": "csv"}}],
                "reasoning": "Data export request",
                "suggestions": ["Filter before export", "Try Excel format", "Email the report"]
            }
        
        # Count/statistics requests
        if "how many" in msg_lower:
            if "vendor" in msg_lower:
                return {
                    "analysis": "User wants vendor count",
                    "tools_to_use": [{"tool": "filter_data", "parameters": {"dataset": "invoices"}}],
                    "reasoning": "Need invoice data to count vendors",
                    "suggestions": ["Filter by specific vendor", "Show vendor performance", "Export vendor list"]
                }
        
        # Default: No tools needed
        return {
            "analysis": "General conversation or greeting",
            "tools_to_use": [],
            "reasoning": "No data access needed",
            "suggestions": ["Filter invoices", "View tickets", "Export data"]
        }
    
    def _build_intelligent_response(self, message: str, plan, execution_result: Dict, user_context) -> str:
        """Build user-friendly response with natural language answers first"""
        
        # Get the step results for analysis
        step_results = execution_result.get('results', [])
        msg_lower = message.lower()
        
        # Generate natural language answer based on the question type
        natural_answer = self._generate_natural_answer(message, step_results, plan)
        
        # Generate trace summary for optional viewing
        trace_summary = self._generate_trace_summary(plan, execution_result, step_results)
        
        # Combine natural answer with trace (trace will be handled by frontend)
        return {
            "natural_response": natural_answer,
            "trace_summary": trace_summary,
            "show_traces": len(step_results) > 1 or execution_result.get('failed_steps', 0) > 0
        }
    
    def _generate_natural_answer(self, message: str, step_results: list, plan) -> str:
        """Generate natural, conversational response using LLM for better quality"""
        
        # First try to get a smart answer using data from step results
        data_summary = self._extract_data_summary(step_results)
        
        # Use LLM to generate a natural response
        if self.llm and self.llm.is_any_provider_available():
            try:
                return self._generate_llm_response(message, data_summary, step_results, plan)
            except Exception as e:
                print(f"LLM response generation failed: {e}")
                # Fall back to pattern-based responses
        
        # Fallback to pattern-based responses
        msg_lower = message.lower()
        
        if "why" in msg_lower and ("fail" in msg_lower or "error" in msg_lower):
            return self._answer_failure_analysis(step_results)
        elif "how many" in msg_lower and "fail" in msg_lower:
            return self._answer_failure_count(step_results)
        elif "filter" in msg_lower:
            return self._answer_filter_request(step_results, message)
        elif "create" in msg_lower and "ticket" in msg_lower:
            return self._answer_ticket_creation(step_results)
        elif "export" in msg_lower or "download" in msg_lower:
            return self._answer_export_request(step_results)
        else:
            return self._answer_generic_request(step_results, plan)
    
    def _extract_data_summary(self, step_results: list) -> Dict[str, Any]:
        """Extract key data from step results for LLM context"""
        summary = {
            "steps_executed": len(step_results),
            "successful_steps": len([r for r in step_results if r.get('status') == 'completed']),
            "data_found": {}
        }
        
        for step_result in step_results:
            if step_result.get('status') == 'completed':
                tool_name = step_result.get('tool_name')
                result_data = step_result.get('result', {}).get('data', {})
                
                if tool_name == 'filter_data' and result_data:
                    summary['data_found']['filtered_records'] = result_data.get('filtered_records', 0)
                    summary['data_found']['total_records'] = result_data.get('total_records', 0)
                    summary['data_found']['filters'] = result_data.get('filters_applied', {})
                    
                elif tool_name == 'analyze_data' and result_data:
                    summary['data_found']['failed_count'] = result_data.get('total_failed', 0)
                    summary['data_found']['failure_reasons'] = result_data.get('failure_reasons', {})
                    summary['data_found']['recommendations'] = result_data.get('recommendations', [])
                    
                elif tool_name == 'create_ticket' and result_data:
                    summary['data_found']['ticket_id'] = result_data.get('id', 'Unknown')
                    summary['data_found']['ticket_title'] = result_data.get('title', '')
        
        return summary
    
    def _generate_llm_response(self, message: str, data_summary: Dict, step_results: list, plan) -> str:
        """Use LLM to generate natural, conversational response"""
        
        # Build context for LLM
        context_parts = [
            f"User asked: '{message}'",
            f"I executed {data_summary['successful_steps']} steps successfully."
        ]
        
        # Add data context
        data_found = data_summary.get('data_found', {})
        if data_found.get('filtered_records') is not None:
            filters = data_found.get('filters', {})
            filter_desc = []
            if filters.get('period'):
                filter_desc.append(f"from {filters['period']}")
            if filters.get('status'):
                filter_desc.append(f"with status '{filters['status']}'")
            if filters.get('vendor'):
                filter_desc.append(f"from vendor {filters['vendor']}")
            
            filter_text = " ".join(filter_desc) if filter_desc else ""
            context_parts.append(f"Found {data_found['filtered_records']} invoices {filter_text} out of {data_found.get('total_records', 0)} total.")
        
        if data_found.get('failed_count') is not None:
            context_parts.append(f"Analysis shows {data_found['failed_count']} failed invoices.")
            
            failure_reasons = data_found.get('failure_reasons', {})
            if failure_reasons:
                reasons_text = []
                for reason, count in failure_reasons.items():
                    reasons_text.append(f"{count} due to {reason}")
                context_parts.append(f"Failure breakdown: {', '.join(reasons_text)}.")
        
        if data_found.get('ticket_id'):
            context_parts.append(f"Created ticket {data_found['ticket_id']} for '{data_found.get('ticket_title', 'user request')}'.")
        
        context = " ".join(context_parts)
        
        prompt = f"""You are FinkraftAI, a helpful business assistant. 

Context: {context}

Generate a natural, conversational response to the user's question. Be helpful, concise, and professional. 
- Answer their specific question directly
- Use natural language, not technical terms
- Be conversational but informative
- If there are actionable insights, mention them
- Keep it under 3 sentences unless complex analysis is needed

User question: "{message}"

Response:"""
        
        try:
            response = self.llm.generate_response(prompt)
            return response.strip()
        except Exception as e:
            print(f"LLM generation error: {e}")
            raise
    
    def _answer_failure_analysis(self, step_results: list) -> str:
        """Natural answer for 'why did they fail?' questions"""
        
        for step_result in step_results:
            if step_result.get('tool_name') == 'analyze_data':
                analysis_data = step_result['result'].get('data', {})
                if analysis_data:
                    total_failed = analysis_data.get('total_failed', 0)
                    failure_reasons = analysis_data.get('failure_reasons', {})
                    
                    if total_failed == 0:
                        return "Good news! I didn't find any failed invoices in the current data."
                    
                    # Build natural explanation
                    responses = [f"I found {total_failed} failed invoices. Here's what went wrong:"]
                    
                    if failure_reasons:
                        for reason, count in sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True):
                            if count == 1:
                                responses.append(f"• 1 invoice failed due to: {reason}")
                            else:
                                responses.append(f"• {count} invoices failed due to: {reason}")
                        
                        # Add helpful recommendation
                        if 'GSTIN' in str(failure_reasons).upper():
                            responses.append("\nThe main issue seems to be missing GSTIN information. I'd recommend contacting the affected vendors to provide their GSTIN details.")
                        elif 'TAX' in str(failure_reasons).upper():
                            responses.append("\nThere appear to be tax calculation issues. You might want to review your tax setup.")
                    else:
                        responses.append("The system shows these invoices as failed, but no specific error messages are available.")
                    
                    return "\n".join(responses)
        
        # Fallback if no analysis found
        return "I'll need to analyze the failed invoices first. Let me filter them for you and then provide the failure reasons."
    
    def _answer_failure_count(self, step_results: list) -> str:
        """Natural answer for 'how many failed?' questions"""
        
        for step_result in step_results:
            if step_result.get('tool_name') == 'filter_data':
                result_data = step_result['result'].get('data', {})
                if result_data and result_data.get('filters_applied', {}).get('status') == 'failed':
                    failed_count = result_data.get('filtered_records', 0)
                    total_count = result_data.get('total_records', 0)
                    
                    if failed_count == 0:
                        return "Great news! I didn't find any failed invoices."
                    elif failed_count == 1:
                        return f"I found 1 failed invoice out of {total_count} total invoices."
                    else:
                        return f"I found {failed_count} failed invoices out of {total_count} total invoices."
        
        return "Let me check the failed invoices for you."
    
    def _answer_filter_request(self, step_results: list, message: str) -> str:
        """Natural answer for filter requests"""
        
        for step_result in step_results:
            if step_result.get('tool_name') == 'filter_data':
                result_data = step_result['result'].get('data', {})
                if result_data:
                    filtered = result_data.get('filtered_records', 0)
                    filters = result_data.get('filters_applied', {})
                    
                    # Build natural description
                    filter_parts = []
                    if filters.get('period'):
                        filter_parts.append(f"from {filters['period']}")
                    if filters.get('vendor'):
                        filter_parts.append(f"from {filters['vendor']}")
                    if filters.get('status'):
                        filter_parts.append(f"with status '{filters['status']}'")
                    
                    if filtered == 0:
                        return f"I didn't find any invoices matching your criteria."
                    elif filtered == 1:
                        filter_desc = " ".join(filter_parts) if filter_parts else ""
                        return f"I found 1 invoice {filter_desc}."
                    else:
                        filter_desc = " ".join(filter_parts) if filter_parts else ""
                        return f"I found {filtered} invoices {filter_desc}."
        
        return "Let me filter the invoices for you."
    
    def _answer_ticket_creation(self, step_results: list) -> str:
        """Natural answer for ticket creation"""
        
        for step_result in step_results:
            if step_result.get('tool_name') == 'create_ticket':
                ticket_data = step_result['result'].get('data', {})
                if ticket_data:
                    ticket_id = ticket_data.get('id', 'Unknown')
                    title = ticket_data.get('title', 'your request')
                    return f"I've created ticket {ticket_id} for {title}. You can track its progress in your tickets dashboard."
        
        return "I've created the support ticket for you."
    
    def _answer_export_request(self, step_results: list) -> str:
        """Natural answer for export requests"""
        
        for step_result in step_results:
            if step_result.get('tool_name') == 'export_report':
                result_data = step_result['result'].get('data', {})
                if result_data:
                    filename = result_data.get('filename', 'your report')
                    record_count = result_data.get('record_count', 0)
                    return f"I've exported {record_count} records to {filename}. You can download it now."
        
        return "I've prepared your export file for download."
    
    def _answer_generic_request(self, step_results: list, plan) -> str:
        """Generic natural answer when we can't determine specific intent"""
        
        if not step_results:
            return "I wasn't able to complete your request. Please try again or contact support if the issue persists."
        
        completed_steps = len([r for r in step_results if r.get('status') == 'completed'])
        total_steps = len(step_results)
        
        if completed_steps == total_steps:
            return f"I've completed your request successfully. {plan.goal if hasattr(plan, 'goal') else ''}"
        else:
            return f"I partially completed your request ({completed_steps} of {total_steps} steps successful)."
    
    def _generate_trace_summary(self, plan, execution_result: Dict, step_results: list) -> str:
        """Generate technical trace summary for optional viewing"""
        
        responses = []
        
        # Add plan info
        if plan.total_steps > 1:
            responses.append(f"🎯 **Plan**: {plan.goal} ({plan.total_steps} steps)")
        
        # Add step details
        for step_result in step_results:
            step_num = step_result['step']
            description = step_result['description']
            status = step_result['status']
            reasoning = step_result.get('reasoning', '')
            
            status_icon = "✅" if status == "completed" else "❌"
            responses.append(f"{status_icon} **Step {step_num}**: {description}")
            if reasoning:
                responses.append(f"   *Reasoning*: {reasoning}")
        
        # Add timing
        exec_time = execution_result.get('execution_time_ms', 0)
        completed = execution_result.get('completed_steps', 0)
        total = execution_result.get('total_steps', 0)
        
        responses.append(f"⏱️ **Execution**: {completed}/{total} steps completed in {exec_time}ms")
        
        return "\n".join(responses)
    
    def _has_personal_data(self, text: str) -> bool:
        """Check if response contains personal data (don't cache)"""
        personal_indicators = ['you typically', 'your last', 'remember when you']
        return any(indicator in text.lower() for indicator in personal_indicators)
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        text = text.strip()
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]
        return text
    
    # Simplified conversation history methods
    def search_conversation_history(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search conversation history"""
        try:
            return memory_manager.search_memory(user_id, query, limit)
        except:
            return []
    
    def get_conversation_threads(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's conversation threads"""
        try:
            threads = db_manager.execute_query("""
                SELECT thread_id, title, is_active, 
                       datetime(started_at) as started_at,
                       datetime(last_activity) as last_activity
                FROM conversation_threads
                WHERE user_id = ?
                ORDER BY last_activity DESC
                LIMIT 20
            """, (user_id,))
            return [dict(thread) for thread in threads] if threads else []
        except Exception as e:
            print(f"Error getting threads: {e}")
            return []
    
    def get_thread_messages(self, user_id: str, thread_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get messages from a specific conversation thread"""
        try:
            messages = db_manager.execute_query("""
                SELECT role, message, tool_name, tool_parameters, tool_result,
                       datetime(timestamp) as timestamp
                FROM conversations
                WHERE user_id = ? AND thread_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
            """, (user_id, thread_id, limit))
            
            return [{
                "role": msg['role'],
                "message": msg['message'],
                "timestamp": msg['timestamp'],
                "tool_used": msg['tool_name'],
                "parameters": json.loads(msg['tool_parameters']) if msg['tool_parameters'] else None,
                "tool_result": json.loads(msg['tool_result']) if msg['tool_result'] else None
            } for msg in messages] if messages else []
        except Exception as e:
            print(f"Error getting thread messages: {e}")
            return []
    
    def switch_conversation_thread(self, user_id: str, thread_id: str) -> bool:
        """Switch to a specific conversation thread"""
        try:
            # Deactivate current threads
            db_manager.execute_query("""
                UPDATE conversation_threads 
                SET is_active = 0
                WHERE user_id = ?
            """, (user_id,))
            
            # Activate specified thread
            result = db_manager.execute_query("""
                UPDATE conversation_threads 
                SET is_active = 1, last_activity = CURRENT_TIMESTAMP
                WHERE thread_id = ? AND user_id = ?
            """, (thread_id, user_id))
            return True
        except Exception as e:
            print(f"Error switching thread: {e}")
            return False
    
    def get_memory_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user's memory and patterns"""
        try:
            # Get basic stats
            conv_stats = db_manager.execute_query("""
                SELECT COUNT(DISTINCT thread_id) as total_threads,
                       COUNT(*) as total_messages,
                       MAX(datetime(timestamp)) as last_activity
                FROM conversations
                WHERE user_id = ?
            """, (user_id,), fetch_one=True)
            
            # Get patterns
            patterns = db_manager.execute_query("""
                SELECT memory_key, memory_value, evidence_count
                FROM user_memory
                WHERE user_id = ? AND memory_type = 'pattern'
                ORDER BY evidence_count DESC
                LIMIT 5
            """, (user_id,))
            
            return {
                'stats': dict(conv_stats) if conv_stats else {},
                'patterns': [dict(p) for p in patterns] if patterns else [],
                'insights': [],
                'suggestions': []
            }
        except Exception as e:
            print(f"Error getting insights: {e}")
            return {'stats': {}, 'patterns': [], 'insights': [], 'suggestions': []}

# Global memory-aware agent instance
memory_aware_agent = MemoryAwareAgent()