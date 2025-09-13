# Memory and context continuity service

from typing import Dict, List, Optional, Any
from backend.core.memory_manager import memory_manager
from backend.core.context_manager import context_manager
from backend.models.conversation import ConversationMessage, ConversationThread
from database.connection import db_manager
import time
import uuid


class ConversationService:
    """Service for managing conversations with memory and context"""
    
    def __init__(self):
        pass
    
    def start_conversation(self, user_id: str, title: str = None, 
                          conversation_type: str = "general", 
                          workspace_id: str = "default") -> str:
        """Start a new conversation thread"""
        
        # Generate title if not provided
        if not title:
            title = f"Conversation {time.strftime('%Y-%m-%d %H:%M')}"
        
        # Create conversation thread
        thread_id = memory_manager.start_conversation_thread(
            user_id=user_id,
            title=title,
            thread_type=conversation_type
        )
        
        # Update user context
        context_manager.set_active_thread(user_id, thread_id, workspace_id)
        
        return thread_id
    
    def add_message(self, user_id: str, role: str, message: str,
                   thread_id: str = None, session_id: str = None,
                   tool_name: str = None, tool_parameters: Dict = None,
                   tool_result: Dict = None, importance_score: float = 0.5,
                   workspace_id: str = "default") -> int:
        """Add a message to conversation with context tracking"""
        
        # Get or create thread
        if not thread_id:
            thread_id = memory_manager.get_active_thread(user_id, session_id)
            if not thread_id:
                thread_id = self.start_conversation(user_id, workspace_id=workspace_id)
        
        # Store conversation with memory
        conversation_id = memory_manager.store_conversation(
            user_id=user_id,
            role=role,
            message=message,
            thread_id=thread_id,
            session_id=session_id,
            tool_name=tool_name,
            tool_parameters=tool_parameters,
            tool_result=tool_result,
            importance_score=importance_score
        )
        
        # Update context
        context_manager.set_active_thread(user_id, thread_id, workspace_id)
        
        if tool_name:
            context_manager.track_tool_usage(user_id, tool_name, workspace_id)
        
        return conversation_id
    
    def get_conversation_history(self, user_id: str, thread_id: str = None,
                               limit: int = 50, workspace_id: str = "default") -> List[Dict[str, Any]]:
        """Get conversation history for a thread"""
        
        if not thread_id:
            thread_id = memory_manager.get_active_thread(user_id)
            if not thread_id:
                return []
        
        # Get messages from database
        messages = db_manager.execute_query("""
            SELECT id, role, message, tool_name, tool_parameters, tool_result,
                   timestamp, importance_score, message_type
            FROM conversations
            WHERE thread_id = ? AND user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (thread_id, user_id, limit))
        
        return [dict(msg) for msg in reversed(messages)]
    
    def search_conversations(self, user_id: str, query: str, 
                           limit: int = 10, workspace_id: str = "default") -> List[Dict[str, Any]]:
        """Search user's conversation history"""
        
        return memory_manager.search_memory(user_id, query, limit)
    
    def get_conversation_context(self, user_id: str, current_message: str,
                               thread_id: str = None, workspace_id: str = "default") -> Dict[str, Any]:
        """Get rich conversation context for LLM"""
        
        return memory_manager.get_conversation_context(user_id, current_message, thread_id)
    
    def get_user_threads(self, user_id: str, workspace_id: str = "default",
                        active_only: bool = False, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's conversation threads"""
        
        query = """
            SELECT thread_id, title, description, started_at, last_activity,
                   thread_type, is_active
            FROM conversation_threads
            WHERE user_id = ?
        """
        params = [user_id]
        
        if workspace_id != "default":
            query += " AND workspace_id = ?"
            params.append(workspace_id)
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY last_activity DESC LIMIT ?"
        params.append(limit)
        
        threads = db_manager.execute_query(query, tuple(params))
        return [dict(thread) for thread in threads]
    
    def switch_thread(self, user_id: str, thread_id: str, 
                     workspace_id: str = "default") -> bool:
        """Switch to a different conversation thread"""
        
        # Verify thread belongs to user
        thread_info = db_manager.execute_query("""
            SELECT thread_id FROM conversation_threads
            WHERE thread_id = ? AND user_id = ?
        """, (thread_id, user_id), fetch_one=True)
        
        if not thread_info:
            return False
        
        # Update context
        context_manager.set_active_thread(user_id, thread_id, workspace_id)
        
        # Activate thread
        db_manager.execute_query("""
            UPDATE conversation_threads 
            SET is_active = 1, last_activity = CURRENT_TIMESTAMP
            WHERE thread_id = ?
        """, (thread_id,))
        
        return True
    
    def archive_thread(self, user_id: str, thread_id: str) -> bool:
        """Archive a conversation thread"""
        
        # Verify ownership
        thread_info = db_manager.execute_query("""
            SELECT thread_id FROM conversation_threads
            WHERE thread_id = ? AND user_id = ?
        """, (thread_id, user_id), fetch_one=True)
        
        if not thread_info:
            return False
        
        # Archive thread
        db_manager.execute_query("""
            UPDATE conversation_threads 
            SET is_active = 0
            WHERE thread_id = ?
        """, (thread_id,))
        
        return True
    
    def update_thread_metadata(self, user_id: str, thread_id: str,
                              title: str = None, description: str = None) -> bool:
        """Update thread title and description"""
        
        # Verify ownership
        thread_info = db_manager.execute_query("""
            SELECT thread_id FROM conversation_threads
            WHERE thread_id = ? AND user_id = ?
        """, (thread_id, user_id), fetch_one=True)
        
        if not thread_info:
            return False
        
        # Update metadata
        updates = []
        params = []
        
        if title:
            updates.append("title = ?")
            params.append(title)
        
        if description:
            updates.append("description = ?")
            params.append(description)
        
        if not updates:
            return False
        
        params.append(thread_id)
        
        query = f"""
            UPDATE conversation_threads 
            SET {', '.join(updates)}
            WHERE thread_id = ?
        """
        
        db_manager.execute_query(query, tuple(params))
        return True
    
    def get_conversation_summary(self, user_id: str, thread_id: str) -> Optional[str]:
        """Get or generate conversation summary"""
        
        # Check for existing summary
        summary = db_manager.execute_query("""
            SELECT summary_text FROM conversation_summaries
            WHERE thread_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (thread_id,), fetch_one=True)
        
        if summary:
            return summary['summary_text']
        
        # Generate new summary (simplified)
        messages = self.get_conversation_history(user_id, thread_id, limit=20)
        
        if not messages:
            return None
        
        # Simple summary generation
        topics = set()
        tools_used = set()
        
        for msg in messages:
            if msg.get('tool_name'):
                tools_used.add(msg['tool_name'])
            
            # Extract key topics (simplified)
            message_text = msg.get('message', '').lower()
            if 'invoice' in message_text:
                topics.add('invoices')
            if 'ticket' in message_text:
                topics.add('tickets')
            if 'vendor' in message_text:
                topics.add('vendors')
        
        summary_text = f"Conversation covering {', '.join(topics)} using tools: {', '.join(tools_used)}"
        
        # Store summary
        db_manager.execute_query("""
            INSERT INTO conversation_summaries (thread_id, summary_text, summary_type)
            VALUES (?, ?, 'auto')
        """, (thread_id, summary_text))
        
        return summary_text
    
    def get_conversation_stats(self, user_id: str, workspace_id: str = "default") -> Dict[str, Any]:
        """Get conversation statistics for user"""
        
        stats = db_manager.execute_query("""
            SELECT 
                COUNT(DISTINCT thread_id) as total_threads,
                COUNT(*) as total_messages,
                COUNT(DISTINCT DATE(timestamp)) as active_days,
                AVG(importance_score) as avg_importance
            FROM conversations
            WHERE user_id = ?
        """, (user_id,), fetch_one=True)
        
        # Get recent activity
        recent_activity = db_manager.execute_query("""
            SELECT COUNT(*) as recent_messages
            FROM conversations
            WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')
        """, (user_id,), fetch_one=True)
        
        result = dict(stats) if stats else {}
        result.update(dict(recent_activity) if recent_activity else {})
        
        return result


# Global conversation service instance
conversation_service = ConversationService()