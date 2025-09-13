# Memory-Aware Gemini Agent - ChatGPT-style intelligence with comprehensive memory

import json
import google.generativeai as genai
from typing import Dict, Any, List
from backend.tools.base_tool import UserContext
from backend.core.tool_registry import registry
from backend.core.memory_manager import memory_manager
from backend.core.vector_store import vector_store
from backend.core.planning_engine import planning_engine
from backend.services.trace_service import trace_service
from database.connection import db_manager

# Configure Gemini
genai.configure(api_key="")

class MemoryAwareAgent:
    """
    Advanced LLM agent with comprehensive memory system
    Provides ChatGPT-style conversation continuity and intelligence
    """
    
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def process_message(self, message: str, user_context: UserContext, 
                       session_id: str = None) -> Dict[str, Any]:
        """Process user message with full memory context"""
        
        try:
            # Get comprehensive memory context
            memory_context = memory_manager.get_conversation_context(
                user_context.user_id, message
            )
            
            # Get active thread
            thread_id = memory_manager.get_active_thread(user_context.user_id, session_id)
            
            # Create execution trace
            trace_id = trace_service.create_execution_trace(
                user_context.user_id, message, workspace_id=user_context.workspace_id
            )
            
            # Step 1: Planning with memory context
            planning_response = self._plan_with_memory(message, user_context, memory_context)
            
            # Log planning in trace
            trace_service.update_trace_plan(trace_id, str(planning_response))
            
            # Store user message in memory
            conversation_id = memory_manager.store_conversation(
                user_context.user_id, 'user', message, thread_id, session_id
            )
            
            if not planning_response.get('tool_call'):
                # No tool needed, generate response with memory
                response_text = planning_response.get('response', 'How can I help you?')
                
                # Store assistant response
                memory_manager.store_conversation(
                    user_context.user_id, 'assistant', response_text, 
                    thread_id, session_id, importance_score=0.3
                )
                
                return {
                    'success': True,
                    'message': response_text,
                    'tool_used': None,
                    'memory_context': memory_context,
                    'planning': planning_response
                }
            
            # Check if this is an execution plan instead of a simple tool call
            if planning_response.get('execution_plan'):
                # Handle execution plan response
                if planning_response.get('auto_executed'):
                    # Plan was executed automatically
                    execution_result = planning_response['execution_result']
                    response_text = self._generate_plan_response(
                        message, planning_response, execution_result, user_context, memory_context
                    )
                    
                    # Store plan execution in memory
                    memory_manager.store_conversation(
                        user_context.user_id, 'assistant', response_text,
                        thread_id, session_id, 'execution_plan', 
                        {'plan_id': planning_response['plan_id']},
                        execution_result, importance_score=0.9
                    )
                    
                    return {
                        'success': execution_result.get('success', False),
                        'message': response_text,
                        'tool_used': 'execution_plan',
                        'plan_id': planning_response['plan_id'],
                        'execution_result': execution_result,
                        'memory_context': memory_context,
                        'planning': planning_response
                    }
                else:
                    # Plan created but needs approval/manual execution
                    response_text = f"I've created a comprehensive execution plan for: {message}\n\n"
                    response_text += f"Plan: {planning_response['plan_details']['description']}\n"
                    response_text += f"Steps: {planning_response['plan_details']['steps']}\n"
                    if planning_response['plan_details']['approval_required']:
                        response_text += "\nThis plan requires approval before execution."
                    else:
                        response_text += f"\nPlan ID: {planning_response['plan_id']} - Ready to execute when you're ready!"
                    
                    memory_manager.store_conversation(
                        user_context.user_id, 'assistant', response_text,
                        thread_id, session_id, importance_score=0.7
                    )
                    
                    return {
                        'success': True,
                        'message': response_text,
                        'tool_used': 'plan_creation',
                        'plan_id': planning_response['plan_id'],
                        'plan_details': planning_response['plan_details'],
                        'memory_context': memory_context,
                        'planning': planning_response
                    }
            
            # Step 2: Execute planned tool (simple tool execution)
            tool_name = planning_response['tool_call']['name']
            parameters = planning_response['tool_call']['parameters']
            
            # Update session state with current tool execution
            if session_id:
                memory_manager.update_session_state(
                    user_context.user_id, session_id, 'current_tool', {
                        'tool': tool_name,
                        'parameters': parameters,
                        'timestamp': memory_context.get('timestamp')
                    }
                )
            
            result = registry.execute_tool(tool_name, parameters, user_context)
            
            # Log tool execution in trace
            trace_service.add_tool_execution(
                trace_id, tool_name, parameters, result.data, 
                result.status, execution_time_ms=0
            )
            
            # Step 3: Generate memory-aware response
            final_response = self._generate_memory_aware_response(
                message, planning_response, result, user_context, memory_context
            )
            
            # Complete trace with explanation
            trace_service.complete_trace(trace_id, final_response)
            
            # Store tool execution in memory
            memory_manager.store_conversation(
                user_context.user_id, 'assistant', final_response,
                thread_id, session_id, tool_name, parameters, 
                result.data, importance_score=0.8
            )
            
            # Update user patterns based on successful execution
            if result.status == 'success':
                memory_manager.update_user_patterns(
                    user_context.user_id, message, tool_name, {'data': result.data}
                )
            
            return {
                'success': result.status == 'success',
                'message': final_response,
                'tool_used': tool_name,
                'parameters': parameters,
                'tool_result': result.data,
                'memory_context': memory_context,
                'planning': planning_response,
                'conversation_id': conversation_id,
                'thread_id': thread_id,
                'trace_id': trace_id
            }
            
        except Exception as e:
            # Store error in memory for learning
            error_message = f"I encountered an error: {str(e)}"
            memory_manager.store_conversation(
                user_context.user_id, 'assistant', error_message,
                importance_score=0.2
            )
            
            return {
                'success': False,
                'message': error_message,
                'tool_used': None,
                'error': str(e)
            }
    
    def _plan_with_memory(self, message: str, user_context: UserContext, 
                         memory_context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced planning that considers user's memory and patterns"""
        
        # First check if this needs complex planning
        plan_analysis = planning_engine.analyze_request(message, user_context)
        
        if plan_analysis["needs_planning"] and plan_analysis["confidence"] > 0.6:
            # This needs a complex execution plan
            return self._create_execution_plan(message, user_context, plan_analysis)
        else:
            # Use simple tool planning
            tools_schema = self._get_tools_schema(user_context)
            memory_prompt = self._build_memory_prompt(message, user_context, memory_context, tools_schema)
            
            response = self.model.generate_content(memory_prompt)
            response_text = self._extract_json(response.text)
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                return {
                    "tool_call": None,
                    "response": "I understand you want help, but I need you to be more specific about what you'd like me to do.",
                    "reasoning": "Could not parse planning response"
                }
    
    def _create_execution_plan(self, message: str, user_context: UserContext, 
                             plan_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create and potentially execute a complex plan"""
        
        # Determine the best template
        template_name = None
        if plan_analysis["template_matches"]:
            template_name = plan_analysis["template_matches"][0]  # Use first match
        
        # Extract any parameters from the message
        custom_params = self._extract_plan_parameters(message, user_context)
        
        # Create the execution plan
        try:
            plan = planning_engine.create_plan(
                goal=message,
                user_context=user_context,
                template_name=template_name,
                custom_params=custom_params
            )
            
            # For simple plans or high confidence, auto-execute
            if (not plan.approval_required and 
                len(plan.steps) <= 3 and 
                plan_analysis["confidence"] > 0.8):
                
                # Execute the plan immediately
                execution_result = planning_engine.execute_plan_sync(plan.plan_id, user_context)
                
                return {
                    "execution_plan": True,
                    "plan_id": plan.plan_id,
                    "auto_executed": True,
                    "execution_result": execution_result,
                    "reasoning": f"Created and executed {len(plan.steps)}-step plan using template '{template_name}'"
                }
            else:
                # Return plan for approval/manual execution
                return {
                    "execution_plan": True,
                    "plan_id": plan.plan_id,
                    "auto_executed": False,
                    "plan_details": {
                        "goal": plan.goal,
                        "description": plan.description,
                        "steps": len(plan.steps),
                        "approval_required": plan.approval_required
                    },
                    "reasoning": f"Created {len(plan.steps)}-step execution plan. " + 
                               ("Requires approval." if plan.approval_required else "Ready to execute.")
                }
                
        except Exception as e:
            return {
                "tool_call": None,
                "response": f"I can help you with that, but I encountered an issue creating the execution plan: {str(e)}",
                "reasoning": "Plan creation failed"
            }
    
    def _extract_plan_parameters(self, message: str, user_context: UserContext) -> Dict[str, Any]:
        """Extract parameters for plan execution from user message"""
        
        params = {}
        message_lower = message.lower()
        
        # Extract vendor names
        import re
        vendor_match = re.search(r'vendor[=:\s]+[\'"]?(\w+)[\'"]?', message_lower)
        if vendor_match:
            params["vendor_name"] = vendor_match.group(1).title()
        
        # Extract specific vendor mentions
        known_vendors = ["indisky", "techsolutions", "global", "automotive", "foodsupply"]
        for vendor in known_vendors:
            if vendor in message_lower:
                params["vendor_name"] = vendor.title()
                break
        
        # Extract time periods
        if "last month" in message_lower:
            params["period"] = "last month"
        elif "last week" in message_lower:
            params["period"] = "last week"
        elif "monthly" in message_lower:
            params["period"] = "monthly"
        
        # Extract status filters
        if "failed" in message_lower:
            params["status"] = "failed"
        elif "pending" in message_lower:
            params["status"] = "pending"
        
        return params
    
    def _build_memory_prompt(self, message: str, user_context: UserContext, 
                           memory_context: Dict[str, Any], tools_schema: List[Dict]) -> str:
        """Build comprehensive prompt with memory context"""
        
        # Recent conversation context
        recent_context = ""
        if memory_context['recent_messages']:
            recent_msgs = memory_context['recent_messages'][:5]  # Last 5 messages
            recent_context = "\nRecent conversation:\n"
            for msg in reversed(recent_msgs):
                role = msg['role']
                content = msg['message'][:200]  # Truncate long messages
                recent_context += f"{role}: {content}\n"
        
        # User patterns and preferences
        patterns_context = ""
        if memory_context['user_patterns']:
            patterns_context = "\nUser patterns and preferences:\n"
            for pattern_key, pattern_data in memory_context['user_patterns'].items():
                if pattern_data['evidence'] > 2:  # Only well-established patterns
                    patterns_context += f"- {pattern_key}: {pattern_data['value']} (confidence: {pattern_data['confidence']:.1f})\n"
        
        # Entity context
        entities_context = ""
        if memory_context['entities']:
            entities_context = "\nReferenced entities:\n"
            for entity in memory_context['entities']:
                entities_context += f"- {entity.get('entity_type', 'unknown')}: {entity.get('entity_name', 'unknown')}\n"
        
        # Relevant history
        history_context = ""
        if memory_context['relevant_history']:
            history_context = "\nRelevant past conversations:\n"
            for hist in memory_context['relevant_history'][:3]:  # Top 3 relevant
                history_context += f"- {hist['text'][:150]}... (similarity: {hist['similarity']:.2f})\n"
        
        # Session state
        session_context = ""
        if memory_context['session_state']:
            session_context = "\nCurrent session state:\n"
            for key, value in memory_context['session_state'].items():
                session_context += f"- {key}: {str(value)[:100]}\n"
        
        return f"""
You are FinkraftAI, an intelligent business assistant with comprehensive memory.

User: {user_context.user_info['full_name']} ({user_context.role})
Context Summary: {memory_context['summary']}

{recent_context}
{patterns_context}
{entities_context}
{history_context}
{session_context}

Available tools:
{json.dumps(tools_schema, indent=2)}

Current user message: "{message}"

Instructions:
1. Consider the user's conversation history and patterns
2. Resolve any entity references (e.g., "that invoice" → specific invoice from context)
3. Use user's preferred tools and parameters when applicable
4. Continue ongoing tasks or investigations
5. Be proactive based on user patterns

Respond with JSON:

If you need to use a tool:
{{
  "tool_call": {{
    "name": "tool_name",
    "parameters": {{"param1": "value1", "param2": "value2"}}
  }},
  "reasoning": "Why you chose this tool considering user's history and patterns",
  "memory_used": "Brief description of how memory influenced your decision"
}}

If no tool is needed:
{{
  "tool_call": null,
  "response": "Your response considering user's history and context",
  "reasoning": "Why no tool was needed",
  "memory_used": "How memory influenced your response"
}}

Be intelligent about entity resolution and context continuation.
"""
    
    def _generate_memory_aware_response(self, original_message: str, planning: Dict, 
                                      result, user_context: UserContext, 
                                      memory_context: Dict[str, Any]) -> str:
        """Generate response that incorporates memory and shows intelligence"""
        
        tool_call = planning.get('tool_call', {})
        tool_name = tool_call.get('name', '')
        parameters = tool_call.get('parameters', {})
        
        # Build context for response generation
        patterns_info = ""
        if memory_context['user_patterns']:
            top_patterns = sorted(
                memory_context['user_patterns'].items(),
                key=lambda x: x[1]['evidence'],
                reverse=True
            )[:3]
            
            for pattern_key, pattern_data in top_patterns:
                if pattern_data['evidence'] > 2:
                    patterns_info += f"User typically {pattern_key}: {pattern_data['value']}. "
        
        recent_context = ""
        if memory_context['recent_messages']:
            recent_count = len(memory_context['recent_messages'])
            recent_context = f"Continuing our conversation (we've exchanged {recent_count} messages). "
        
        response_prompt = f"""
You are FinkraftAI responding to a user after executing a tool, with full conversation memory.

Original message: "{original_message}"
Tool used: {tool_name}
Parameters: {json.dumps(parameters)}
Tool execution status: {result.status}
Tool result: {json.dumps(result.data) if result.data else 'No data'}
Tool message: {result.message}

Memory context:
{recent_context}
{patterns_info}

User patterns suggest: {memory_context['summary']}

Generate a natural, intelligent response that:
1. Shows you remember previous conversations
2. References relevant context when helpful
3. Suggests next steps based on user patterns
4. Is conversational and helpful
5. Demonstrates understanding of the user's business context

Be proactive if you notice patterns or can suggest improvements.
"""
        
        response = self.model.generate_content(response_prompt)
        return response.text.strip()
    
    def _generate_plan_response(self, original_message: str, planning: Dict, 
                               execution_result: Dict, user_context: UserContext, 
                               memory_context: Dict[str, Any]) -> str:
        """Generate response for executed plans"""
        
        plan_id = planning.get('plan_id', 'unknown')
        success = execution_result.get('success', False)
        completed_steps = execution_result.get('completed_steps', 0)
        total_steps = execution_result.get('total_steps', 0)
        
        if success:
            response_prompt = f"""
You successfully executed a complex business workflow for the user.

Original request: "{original_message}"
Plan executed: {planning.get('reasoning', 'Multi-step plan')}
Plan ID: {plan_id}
Execution result: {completed_steps}/{total_steps} steps completed successfully

Results from execution: {json.dumps(execution_result.get('results', []))}

Generate a comprehensive, professional response that:
1. Acknowledges the completion of the complex workflow
2. Summarizes the key results and findings
3. Highlights any important insights or patterns discovered
4. Suggests logical next steps if appropriate
5. References the plan execution for future reference

Be intelligent about the results and provide business value.
"""
        else:
            response_prompt = f"""
A complex business workflow was attempted but encountered issues.

Original request: "{original_message}"
Plan ID: {plan_id}
Execution status: {completed_steps}/{total_steps} steps completed
Error: {execution_result.get('error', 'Unknown error')}

Generate a helpful response that:
1. Explains what was attempted
2. Describes what was completed successfully
3. Explains what went wrong
4. Suggests how to proceed or troubleshoot
5. Offers alternative approaches

Be supportive and constructive.
"""
        
        response = self.model.generate_content(response_prompt)
        return response.text.strip()
    
    def _get_tools_schema(self, user_context: UserContext) -> List[Dict]:
        """Get available tools schema for the user"""
        
        tools_info = registry.get_available_tools_info(user_context.user_id)
        
        tools_schema = []
        for tool in tools_info:
            properties = {}
            required = []
            
            for param in tool['parameters']:
                properties[param['name']] = {
                    "type": param['type'],
                    "description": param['description']
                }
                if param['required']:
                    required.append(param['name'])
            
            tools_schema.append({
                "name": tool['name'],
                "description": tool['description'],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            })
        
        return tools_schema
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from LLM response"""
        
        text = text.strip()
        
        # Look for JSON in code blocks
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            return text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            return text[start:end].strip()
        
        # Look for JSON objects
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]
        
        return text
    
    def search_conversation_history(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search user's conversation history"""
        return memory_manager.search_memory(user_id, query, limit)
    
    def get_conversation_threads(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's conversation threads"""
        
        threads = db_manager.execute_query("""
            SELECT thread_id, title, description, started_at, last_activity, 
                   thread_type, is_active
            FROM conversation_threads
            WHERE user_id = ?
            ORDER BY last_activity DESC
            LIMIT 20
        """, (user_id,))
        
        return [dict(thread) for thread in threads]
    
    def switch_conversation_thread(self, user_id: str, thread_id: str) -> bool:
        """Switch to a specific conversation thread"""
        
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
        
        return result is not None
    
    def get_memory_insights(self, user_id: str) -> Dict[str, Any]:
        """Get insights about user's memory and patterns"""
        
        stats = memory_manager.get_memory_stats(user_id)
        
        # Add behavioral insights
        insights = {
            'stats': stats,
            'insights': [],
            'suggestions': []
        }
        
        # Analyze patterns for insights
        if 'patterns' in stats:
            if stats['patterns'].get('frequent_tool', 0) > 5:
                insights['insights'].append("You frequently use data filtering tools")
            
            if stats['patterns'].get('frequent_vendor', 0) > 3:
                insights['insights'].append("You often work with specific vendors")
        
        # Generate suggestions
        if stats.get('total_messages', 0) > 10:
            insights['suggestions'].append("You can search your conversation history using natural language")
        
        if stats.get('total_threads', 0) > 3:
            insights['suggestions'].append("Consider organizing conversations by project or topic")
        
        return insights

# Global memory-aware agent instance
memory_aware_agent = MemoryAwareAgent()