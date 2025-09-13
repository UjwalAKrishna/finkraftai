# Comprehensive Memory Manager - ChatGPT-style memory system

import json
import time
import uuid
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from database.connection import db_manager
from backend.core.vector_store import vector_store
import re


class MemoryManager:
    """
    Complete memory management system with contextual, semantic, and episodic memory
    """
    
    def __init__(self):
        self.entity_patterns = {
            'invoice': r'(invoice|INV-\d+)',
            'ticket': r'(ticket|TIC-\d+)',
            'vendor': r'(vendor|supplier|company)',
            'amount': r'\$?[\d,]+\.?\d*',
            'date': r'(today|yesterday|last \w+|this \w+|\d{1,2}/\d{1,2})'
        }
    
    def start_conversation_thread(self, user_id: str, title: str = None, 
                                thread_type: str = "general") -> str:
        """Start a new conversation thread"""
        
        thread_id = f"thread_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Auto-generate title if not provided
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        db_manager.execute_query("""
            INSERT INTO conversation_threads (thread_id, user_id, title, thread_type)
            VALUES (?, ?, ?, ?)
        """, (thread_id, user_id, title, thread_type))
        
        return thread_id
    
    def get_active_thread(self, user_id: str, session_id: str = None) -> Optional[str]:
        """Get user's active conversation thread"""
        
        # First try to get active thread from recent activity
        result = db_manager.execute_query("""
            SELECT thread_id FROM conversation_threads 
            WHERE user_id = ? AND is_active = 1
            ORDER BY last_activity DESC LIMIT 1
        """, (user_id,), fetch_one=True)
        
        if result:
            return result['thread_id']
        
        # Create new thread if none exists
        return self.start_conversation_thread(user_id)
    
    def store_conversation(self, user_id: str, role: str, message: str, 
                         thread_id: str = None, session_id: str = None,
                         tool_name: str = None, tool_parameters: Dict = None,
                         tool_result: Dict = None, importance_score: float = 0.5) -> int:
        """Store conversation message with full context"""
        
        if not thread_id:
            thread_id = self.get_active_thread(user_id, session_id)
        
        # Store conversation
        conversation_id = db_manager.execute_query("""
            INSERT INTO conversations (
                thread_id, user_id, role, message, message_type,
                tool_name, tool_parameters, tool_result, session_id,
                importance_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            thread_id, user_id, role, message,
            'tool_call' if tool_name else 'text',
            tool_name,
            json.dumps(tool_parameters) if tool_parameters else None,
            json.dumps(tool_result) if tool_result else None,
            session_id,
            importance_score
        ))
        
        # Update thread activity
        db_manager.execute_query("""
            UPDATE conversation_threads 
            SET last_activity = CURRENT_TIMESTAMP
            WHERE thread_id = ?
        """, (thread_id,))
        
        # Extract and store entities
        entities = self.extract_entities(message, conversation_id)
        
        # Create vector embedding for semantic search
        if len(message.strip()) > 10:  # Only embed meaningful messages
            metadata = {
                'conversation_id': conversation_id,
                'user_id': user_id,
                'thread_id': thread_id,
                'role': role,
                'content_type': 'message',
                'tool_name': tool_name,
                'importance_score': importance_score,
                'timestamp': datetime.now().isoformat()
            }
            
            vector_store.add_embedding(message, metadata)
        
        # Update user behavioral patterns
        self.update_user_patterns(user_id, message, tool_name, tool_result)
        
        return conversation_id
    
    def extract_entities(self, message: str, conversation_id: int) -> List[Dict[str, Any]]:
        """Extract business entities from message"""
        
        entities = []
        message_lower = message.lower()
        
        # Extract invoice numbers
        invoice_matches = re.findall(r'(INV-\d+|invoice\s+\w+)', message, re.IGNORECASE)
        for match in invoice_matches:
            entities.append({
                'type': 'invoice',
                'id': match.strip(),
                'name': match,
                'context': message,
                'confidence': 0.9
            })
        
        # Extract ticket numbers  
        ticket_matches = re.findall(r'(TIC-\d+|ticket\s+\w+)', message, re.IGNORECASE)
        for match in ticket_matches:
            entities.append({
                'type': 'ticket',
                'id': match.strip(),
                'name': match,
                'context': message,
                'confidence': 0.9
            })
        
        # Extract vendor names (common ones from our business DB)
        vendor_names = ['indisky', 'techsolutions', 'global imports', 'automotive parts', 
                       'foodsupply', 'steel industries', 'electronics hub']
        for vendor in vendor_names:
            if vendor in message_lower:
                entities.append({
                    'type': 'vendor',
                    'id': vendor,
                    'name': vendor.title(),
                    'context': message,
                    'confidence': 0.8
                })
        
        # Store entities in database
        for entity in entities:
            db_manager.execute_query("""
                INSERT INTO entity_mentions (
                    conversation_id, entity_type, entity_id, entity_name,
                    mention_context, confidence_score
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, entity['type'], entity['id'],
                entity['name'], entity['context'], entity['confidence']
            ))
        
        return entities
    
    def update_user_patterns(self, user_id: str, message: str, tool_name: str, tool_result: Dict):
        """Learn user behavioral patterns and preferences"""
        
        patterns_to_update = []
        
        # Track tool usage patterns
        if tool_name:
            patterns_to_update.append(('frequent_tool', tool_name))
            
            # Track specific tool preferences
            if tool_name == 'filter_data' and tool_result:
                data = tool_result.get('data', {})
                if 'dataset' in data.get('filters_applied', {}):
                    dataset = data['filters_applied']['dataset']
                    patterns_to_update.append(('preferred_dataset', dataset))
                
                if 'vendor' in data.get('filters_applied', {}):
                    vendor = data['filters_applied']['vendor']
                    patterns_to_update.append(('frequent_vendor', vendor))
            
            elif tool_name == 'export_report' and tool_result:
                data = tool_result.get('data', {})
                if 'format' in data:
                    format_type = data['format']
                    patterns_to_update.append(('preferred_export_format', format_type))
        
        # Track time patterns
        hour = datetime.now().hour
        if 9 <= hour <= 17:
            patterns_to_update.append(('usage_pattern', 'business_hours'))
        
        # Store/update patterns
        for pattern_type, pattern_value in patterns_to_update:
            # Check if pattern exists
            existing = db_manager.execute_query("""
                SELECT evidence_count FROM user_memory
                WHERE user_id = ? AND memory_key = ? AND memory_value = ?
            """, (user_id, pattern_type, pattern_value), fetch_one=True)
            
            if existing:
                # Increment evidence
                db_manager.execute_query("""
                    UPDATE user_memory 
                    SET evidence_count = evidence_count + 1,
                        last_reinforced = CURRENT_TIMESTAMP,
                        confidence_score = MIN(1.0, confidence_score + 0.1)
                    WHERE user_id = ? AND memory_key = ? AND memory_value = ?
                """, (user_id, pattern_type, pattern_value))
            else:
                # Create new pattern
                db_manager.execute_query("""
                    INSERT OR REPLACE INTO user_memory (
                        user_id, memory_type, memory_key, memory_value, evidence_count
                    ) VALUES (?, 'pattern', ?, ?, 1)
                """, (user_id, pattern_type, pattern_value))
    
    def get_conversation_context(self, user_id: str, current_message: str, 
                               thread_id: str = None, max_messages: int = 20) -> Dict[str, Any]:
        """Build comprehensive context for LLM"""
        
        context = {
            'recent_messages': [],
            'relevant_history': [],
            'entities': [],
            'user_patterns': {},
            'session_state': {},
            'summary': ''
        }
        
        if not thread_id:
            thread_id = self.get_active_thread(user_id)
        
        # Get recent messages from current thread
        recent_messages = db_manager.execute_query("""
            SELECT role, message, tool_name, tool_result, timestamp, importance_score
            FROM conversations
            WHERE thread_id = ? AND user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (thread_id, user_id, max_messages))
        
        context['recent_messages'] = [dict(msg) for msg in recent_messages]
        
        # Get semantically relevant conversations
        if len(current_message.strip()) > 10:
            relevant_conversations = vector_store.search_by_conversation(
                current_message, user_id, k=5, exclude_thread=thread_id
            )
            
            for conv in relevant_conversations:
                if conv['similarity_score'] > 0.7:  # High similarity threshold
                    context['relevant_history'].append({
                        'text': conv['text'],
                        'similarity': conv['similarity_score'],
                        'metadata': conv['metadata']
                    })
        
        # Get mentioned entities
        entities = self.resolve_entity_references(current_message, user_id, thread_id)
        context['entities'] = entities
        
        # Get user patterns
        patterns = db_manager.execute_query("""
            SELECT memory_key, memory_value, confidence_score, evidence_count
            FROM user_memory
            WHERE user_id = ? AND memory_type = 'pattern'
            ORDER BY evidence_count DESC, confidence_score DESC
            LIMIT 10
        """, (user_id,))
        
        for pattern in patterns:
            context['user_patterns'][pattern['memory_key']] = {
                'value': pattern['memory_value'],
                'confidence': pattern['confidence_score'],
                'evidence': pattern['evidence_count']
            }
        
        # Get session state
        session_state = db_manager.execute_query("""
            SELECT state_key, state_value
            FROM session_states
            WHERE user_id = ?
            ORDER BY updated_at DESC
        """, (user_id,))
        
        for state in session_state:
            try:
                context['session_state'][state['state_key']] = json.loads(state['state_value'])
            except:
                context['session_state'][state['state_key']] = state['state_value']
        
        # Generate context summary
        context['summary'] = self.generate_context_summary(context)
        
        return context
    
    def resolve_entity_references(self, message: str, user_id: str, thread_id: str) -> List[Dict[str, Any]]:
        """Resolve entity references like 'that invoice', 'those tickets'"""
        
        entities = []
        message_lower = message.lower()
        
        # Look for reference patterns
        reference_patterns = [
            (r'(that|the|this)\s+(invoice|ticket)', 'recent_single'),
            (r'(those|these)\s+(invoices|tickets)', 'recent_multiple'),
            (r'(it|them)', 'contextual')
        ]
        
        for pattern, ref_type in reference_patterns:
            if re.search(pattern, message_lower):
                # Get recent entities from conversation
                recent_entities = db_manager.execute_query("""
                    SELECT DISTINCT em.entity_type, em.entity_id, em.entity_name
                    FROM entity_mentions em
                    JOIN conversations c ON em.conversation_id = c.id
                    WHERE c.user_id = ? AND c.thread_id = ?
                    ORDER BY c.timestamp DESC
                    LIMIT 5
                """, (user_id, thread_id))
                
                entities.extend([dict(entity) for entity in recent_entities])
                break
        
        return entities
    
    def generate_context_summary(self, context: Dict[str, Any]) -> str:
        """Generate a concise summary of the context"""
        
        summary_parts = []
        
        # Recent activity
        if context['recent_messages']:
            recent_count = len(context['recent_messages'])
            summary_parts.append(f"Recent conversation has {recent_count} messages")
        
        # User patterns
        if context['user_patterns']:
            top_pattern = max(context['user_patterns'].items(), 
                            key=lambda x: x[1]['evidence'], default=None)
            if top_pattern:
                summary_parts.append(f"User frequently {top_pattern[0]}: {top_pattern[1]['value']}")
        
        # Active entities
        if context['entities']:
            entity_types = set(e.get('entity_type') for e in context['entities'])
            summary_parts.append(f"Working with: {', '.join(entity_types)}")
        
        return ". ".join(summary_parts) if summary_parts else "New conversation"
    
    def update_session_state(self, user_id: str, session_id: str, key: str, value: Any):
        """Update session state for stateful conversations"""
        
        db_manager.execute_query("""
            INSERT OR REPLACE INTO session_states (session_id, user_id, state_key, state_value)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_id, key, json.dumps(value)))
    
    def clear_session_state(self, user_id: str, session_id: str = None):
        """Clear session state"""
        
        if session_id:
            db_manager.execute_query("""
                DELETE FROM session_states WHERE user_id = ? AND session_id = ?
            """, (user_id, session_id))
        else:
            db_manager.execute_query("""
                DELETE FROM session_states WHERE user_id = ?
            """, (user_id,))
    
    def search_memory(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search user's memory using semantic search"""
        
        results = vector_store.search_by_conversation(query, user_id, k=limit)
        
        # Enhance results with conversation context
        enhanced_results = []
        for result in results:
            conversation_id = result['metadata'].get('conversation_id')
            if conversation_id:
                # Get full conversation context
                conv_data = db_manager.execute_query("""
                    SELECT role, message, timestamp, tool_name
                    FROM conversations
                    WHERE id = ?
                """, (conversation_id,), fetch_one=True)
                
                if conv_data:
                    enhanced_results.append({
                        'text': result['text'],
                        'similarity': result['similarity_score'],
                        'conversation': dict(conv_data),
                        'metadata': result['metadata']
                    })
        
        return enhanced_results
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user's memory statistics"""
        
        stats = {}
        
        # Conversation stats
        conv_stats = db_manager.execute_query("""
            SELECT 
                COUNT(DISTINCT thread_id) as total_threads,
                COUNT(*) as total_messages,
                AVG(importance_score) as avg_importance,
                MAX(timestamp) as last_activity
            FROM conversations
            WHERE user_id = ?
        """, (user_id,), fetch_one=True)
        
        stats.update(dict(conv_stats) if conv_stats else {})
        
        # Entity stats
        entity_stats = db_manager.execute_query("""
            SELECT entity_type, COUNT(*) as count
            FROM entity_mentions em
            JOIN conversations c ON em.conversation_id = c.id
            WHERE c.user_id = ?
            GROUP BY entity_type
        """, (user_id,))
        
        stats['entities'] = {row['entity_type']: row['count'] for row in entity_stats}
        
        # Pattern stats
        pattern_stats = db_manager.execute_query("""
            SELECT memory_key, COUNT(*) as count
            FROM user_memory
            WHERE user_id = ? AND memory_type = 'pattern'
            GROUP BY memory_key
        """, (user_id,))
        
        stats['patterns'] = {row['memory_key']: row['count'] for row in pattern_stats}
        
        # Vector store stats
        stats['vector_store'] = vector_store.get_stats()
        
        return stats
    
    def cleanup_old_memories(self, days_old: int = 90):
        """Clean up old memories based on retention policy"""
        
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        # Get old conversation IDs
        old_conversations = db_manager.execute_query("""
            SELECT id FROM conversations
            WHERE timestamp < ? AND importance_score < 0.3
        """, (cutoff_date.isoformat(),))
        
        # Delete old embeddings
        for conv in old_conversations:
            vector_store.delete_by_metadata({'conversation_id': conv['id']})
        
        # Delete old conversations (keep summaries)
        db_manager.execute_query("""
            DELETE FROM conversations
            WHERE timestamp < ? AND importance_score < 0.3
        """, (cutoff_date.isoformat(),))
        
        print(f"Cleaned up {len(old_conversations)} old conversations")
    
    def save_memory(self):
        """Save memory state (for shutdown/backup)"""
        vector_store.save_index()
        print("Memory state saved")

# Global memory manager instance
memory_manager = MemoryManager()