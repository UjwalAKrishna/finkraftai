# Optimized Memory Manager - Clean and efficient

import json
import time
import uuid
import re
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from database.connection import db_manager
from backend.core.vector_store import vector_store

class MemoryManager:
    """Efficient memory system with conversation threads and pattern learning"""
    
    def __init__(self):
        # Simple entity patterns for extraction
        self.entity_patterns = {
            'vendor': r'\b(indisky|techsolutions|global|automotive|foodsupply)\b',
            'status': r'\b(failed|pending|approved|rejected)\b',
            'period': r'\b(last|this) (month|week|year)\b'
        }
        self.min_pattern_evidence = 2  # Minimum evidence count for patterns
    
    def get_active_thread(self, user_id: str, session_id: str = None) -> str:
        """Get or create active conversation thread"""
        try:
            result = db_manager.execute_query("""
                SELECT thread_id FROM conversation_threads 
                WHERE user_id = ? AND is_active = 1
                ORDER BY last_activity DESC LIMIT 1
            """, (user_id,), fetch_one=True)
            
            if result:
                return result['thread_id']
            
            # Create new thread
            thread_id = f"thread_{user_id}_{int(time.time())}"
            db_manager.execute_query("""
                INSERT OR IGNORE INTO conversation_threads (thread_id, user_id, title, is_active)
                VALUES (?, ?, ?, 1)
            """, (thread_id, user_id, f"Chat {datetime.now().strftime('%m-%d')}"))
            return thread_id
        except:
            return f"thread_{user_id}_default"
    
    def store_conversation(self, user_id: str, role: str, message: str, 
                         thread_id: str = None, session_id: str = None,
                         tool_name: str = None, tool_parameters: Dict = None,
                         tool_result: Dict = None, importance_score: float = 0.5) -> int:
        """Store conversation message simply"""
        try:
            if not thread_id:
                thread_id = self.get_active_thread(user_id, session_id)
            
            # Store conversation
            conversation_id = db_manager.execute_query("""
                INSERT INTO conversations (
                    thread_id, user_id, role, message, tool_name, tool_parameters, tool_result
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                thread_id, user_id, role, message, tool_name,
                json.dumps(tool_parameters) if tool_parameters else None,
                json.dumps(tool_result) if tool_result else None
            ))
            
            # Update patterns if tool was used
            if tool_name and tool_result:
                self._update_simple_patterns(user_id, tool_name, tool_result)
            
            return conversation_id
        except Exception as e:
            print(f"Error storing conversation: {e}")
            return 0
    
    def _update_simple_patterns(self, user_id: str, tool_name: str, tool_result: Dict):
        """Update basic user patterns"""
        try:
            # Track frequent tools
            db_manager.execute_query("""
                INSERT OR REPLACE INTO user_memory (user_id, memory_type, memory_key, memory_value, evidence_count)
                VALUES (?, 'pattern', 'frequent_tool', ?, 
                    COALESCE((SELECT evidence_count FROM user_memory 
                             WHERE user_id = ? AND memory_key = 'frequent_tool' AND memory_value = ?), 0) + 1)
            """, (user_id, tool_name, user_id, tool_name))
            
            # Track vendor preferences for filter tool
            if tool_name == 'filter_data' and tool_result and tool_result.get('data'):
                filters = tool_result['data'].get('filters_applied', {})
                if filters.get('vendor'):
                    vendor = filters['vendor']
                    db_manager.execute_query("""
                        INSERT OR REPLACE INTO user_memory (user_id, memory_type, memory_key, memory_value, evidence_count)
                        VALUES (?, 'pattern', 'frequent_vendor', ?, 
                            COALESCE((SELECT evidence_count FROM user_memory 
                                     WHERE user_id = ? AND memory_key = 'frequent_vendor' AND memory_value = ?), 0) + 1)
                    """, (user_id, vendor, user_id, vendor))
        except:
            pass
    
    def get_conversation_context(self, user_id: str, current_message: str, 
                               thread_id: str = None, max_messages: int = 5) -> Dict[str, Any]:
        """Get minimal conversation context"""
        try:
            if not thread_id:
                thread_id = self.get_active_thread(user_id)
            
            # Get recent messages only
            recent_messages = db_manager.execute_query("""
                SELECT role, message, tool_name FROM conversations
                WHERE thread_id = ? AND user_id = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (thread_id, user_id, max_messages))
            
            # Get basic patterns
            patterns = db_manager.execute_query("""
                SELECT memory_key, memory_value, evidence_count FROM user_memory
                WHERE user_id = ? AND memory_type = 'pattern' AND evidence_count >= ?
                ORDER BY evidence_count DESC LIMIT 3
            """, (user_id, self.min_pattern_evidence))
            
            return {
                'recent_messages': [dict(msg) for msg in recent_messages],
                'user_patterns': {p['memory_key']: {'value': p['memory_value'], 'evidence': p['evidence_count']} 
                                for p in patterns},
                'entities': [],
                'session_state': {},
                'summary': f"Active conversation with {len(recent_messages)} recent messages"
            }
        except:
            return {'recent_messages': [], 'user_patterns': {}, 'entities': [], 'session_state': {}, 'summary': ''}
    
    def update_session_state(self, user_id: str, session_id: str, key: str, value: Any):
        """Update session state"""
        try:
            db_manager.execute_query("""
                INSERT OR REPLACE INTO session_states (session_id, user_id, state_key, state_value)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_id, key, json.dumps(value)))
        except:
            pass
    
    def search_memory(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Simple memory search"""
        try:
            results = db_manager.execute_query("""
                SELECT role, message, timestamp, tool_name FROM conversations
                WHERE user_id = ? AND message LIKE ?
                ORDER BY timestamp DESC LIMIT ?
            """, (user_id, f'%{query}%', limit))
            return [dict(r) for r in results]
        except:
            return []
    
    # Essential utility methods
    def update_user_patterns(self, user_id: str, message: str, tool_name: str, tool_result: Dict):
        """Legacy method for compatibility"""
        if tool_name and tool_result:
            self._update_simple_patterns(user_id, tool_name, tool_result)

# Global memory manager instance
memory_manager = MemoryManager()