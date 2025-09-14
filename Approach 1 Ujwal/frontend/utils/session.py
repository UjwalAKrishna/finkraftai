# Session management utilities
import streamlit as st
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional

class ConversationManager:
    """Manages conversation history via backend API"""
    
    @staticmethod
    def init_conversation_state():
        """Initialize conversation-related session state"""
        if 'current_thread_id' not in st.session_state:
            st.session_state.current_thread_id = None
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
    
    @staticmethod
    def create_new_conversation(title: str = None) -> str:
        """Create a new conversation thread via backend"""
        import requests
        
        try:
            # Call backend to explicitly create new thread
            response = requests.post(f"http://localhost:8000/memory/{st.session_state.current_user}/threads/new", 
                                   params={"title": title} if title else {})
            
            if response.status_code == 200:
                data = response.json()
                new_thread_id = data.get('thread_id')
                
                # Clear current state and set new thread
                st.session_state.current_thread_id = new_thread_id
                st.session_state.chat_history = []
                
                return new_thread_id
            else:
                st.error(f"Failed to create new conversation: {response.status_code}")
                return None
                
        except Exception as e:
            st.error(f"Error creating new conversation: {e}")
            return None
    
    @staticmethod
    def load_conversation(thread_id: str):
        """Load a specific conversation thread from backend"""
        import requests
        
        try:
            # First, save current conversation if there is one
            ConversationManager.save_current_conversation()
            
            # Activate the thread in backend
            response = requests.post(f"http://localhost:8000/memory/{st.session_state.current_user}/threads/{thread_id}/activate")
            if response.status_code == 200:
                # Clear current state before loading new conversation
                st.session_state.current_thread_id = thread_id
                st.session_state.chat_history = []
                
                # Load conversation history from backend
                ConversationManager.load_chat_history(thread_id)
                
                # Success feedback
                st.success(f"Loaded conversation: {thread_id[:20]}...")
            else:
                st.error(f"Failed to load conversation: {response.status_code}")
        except Exception as e:
            st.error(f"Error loading conversation: {e}")
    
    @staticmethod
    def load_chat_history(thread_id: str):
        """Load chat history for a thread from backend"""
        import requests
        
        try:
            response = requests.get(f"http://localhost:8000/memory/{st.session_state.current_user}/threads/{thread_id}/messages")
            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])
                
                # Convert backend format to frontend format
                formatted_messages = []
                for msg in messages:
                    formatted_msg = {
                        "role": msg["role"],
                        "message": msg["message"],
                        "timestamp": msg["timestamp"],
                        "success": True,
                        "tool_used": msg.get("tool_used"),
                        "parameters": msg.get("parameters"),
                        "trace_data": {
                            "importance_score": msg.get("importance_score", 0)
                        }
                    }
                    
                    # Add tool result data if available
                    if msg.get("tool_result"):
                        formatted_msg["data"] = msg["tool_result"]
                    
                    formatted_messages.append(formatted_msg)
                
                st.session_state.chat_history = formatted_messages
            else:
                st.error(f"Failed to load conversation messages: {response.status_code}")
                st.session_state.chat_history = []
                
        except Exception as e:
            st.error(f"Error loading conversation history: {e}")
            st.session_state.chat_history = []
    
    @staticmethod
    def save_current_conversation():
        """Save is automatic in backend - this is a no-op"""
        pass
    
    @staticmethod
    def delete_conversation(thread_id: str):
        """Delete a conversation thread"""
        # TODO: Implement delete thread API in backend
        if st.session_state.current_thread_id == thread_id:
            st.session_state.current_thread_id = None
            st.session_state.chat_history = []
    
    @staticmethod
    def get_user_conversations(user_id: str) -> List[Dict]:
        """Get all conversation threads for a user from backend"""
        import requests
        
        try:
            response = requests.get(f"http://localhost:8000/memory/{user_id}/threads")
            if response.status_code == 200:
                data = response.json()
                threads = data.get('threads', [])
                
                # Convert backend format to frontend format
                conversations = []
                for thread in threads:
                    conversations.append({
                        'id': thread['thread_id'],
                        'title': thread['title'],
                        'created_at': thread.get('started_at', ''),
                        'updated_at': thread.get('last_activity', ''),
                        'user_id': user_id,
                        'thread_type': thread.get('thread_type', 'general')
                    })
                
                return conversations
            else:
                return []
        except Exception as e:
            st.error(f"Error loading conversations: {e}")
            return []
    
    @staticmethod
    def clear_all_conversations():
        """Clear all conversations (admin function)"""
        st.session_state.current_thread_id = None
        st.session_state.chat_history = []

class SessionManager:
    """Enhanced session management"""
    
    @staticmethod
    def init_session_state():
        """Initialize all session state variables"""
        if 'current_user' not in st.session_state:
            st.session_state.current_user = "john_doe"
        if 'user_permissions' not in st.session_state:
            st.session_state.user_permissions = []
        if 'session_id' not in st.session_state:
            st.session_state.session_id = f"streamlit_{int(datetime.now().timestamp())}"
        
        # Initialize conversation state
        ConversationManager.init_conversation_state()
    
    @staticmethod
    def switch_user(new_user: str):
        """Switch to a different user and load their conversations"""
        if new_user != st.session_state.current_user:
            # Save current conversation before switching
            ConversationManager.save_current_conversation()
            
            # Switch user
            st.session_state.current_user = new_user
            st.session_state.session_id = f"streamlit_{int(datetime.now().timestamp())}"
            
            # Clear current conversation state - user will see their own conversations
            st.session_state.current_conversation_id = None
            st.session_state.chat_history = []
            
            return True
        return False