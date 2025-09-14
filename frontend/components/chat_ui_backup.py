# Chat interface component
import streamlit as st
from datetime import datetime
from utils.session import ConversationManager

def render_conversation_sidebar():
    """Render the conversation history sidebar (like ChatGPT)"""
    
    with st.sidebar:
        # Header with New Chat button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### 💬 Conversations")
        with col2:
            if st.button("➕", help="New Chat", use_container_width=True):
                # Save current conversation
                ConversationManager.save_current_conversation()
                
                # Create new conversation
                ConversationManager.create_new_conversation()
                st.rerun()
        
        st.divider()
        
        # Get user's conversations
        user_conversations = ConversationManager.get_user_conversations(st.session_state.current_user)
        
        if user_conversations:
            # Group conversations by date
            today_convs = []
            yesterday_convs = []
            older_convs = []
            
            current_date = datetime.now().date()
            
            for conv in user_conversations:
                try:
                    # Try different datetime formats that backend might return
                    conv_datetime_str = conv['updated_at']
                    if 'T' in conv_datetime_str:
                        # ISO format: 2023-09-14T14:22:36
                        conv_date = datetime.fromisoformat(conv_datetime_str.split('T')[0]).date()
                    elif len(conv_datetime_str) > 16:
                        # Format with seconds: 2023-09-14 14:22:36
                        conv_date = datetime.strptime(conv_datetime_str[:16], "%Y-%m-%d %H:%M").date()
                    else:
                        # Format without seconds: 2023-09-14 14:22
                        conv_date = datetime.strptime(conv_datetime_str, "%Y-%m-%d %H:%M").date()
                except (ValueError, TypeError):
                    # Fallback to today if parsing fails
                    conv_date = current_date
                
                days_diff = (current_date - conv_date).days
                
                if days_diff == 0:
                    today_convs.append(conv)
                elif days_diff == 1:
                    yesterday_convs.append(conv)
                else:
                    older_convs.append(conv)
            
            # Render conversation groups
            if today_convs:
                st.markdown("**Today**")
                render_conversation_group(today_convs)
                st.divider()
            
            if yesterday_convs:
                st.markdown("**Yesterday**")
                render_conversation_group(yesterday_convs)
                st.divider()
            
            if older_convs:
                st.markdown("**Older**")
                render_conversation_group(older_convs)
        else:
            st.markdown("*No conversations yet*")
            st.markdown("Start a new conversation!")

def render_conversation_group(conversations):
    """Render a group of conversations"""
    for conv in conversations:
        # Create a container for each conversation
        container = st.container()
        
        with container:
            # Check if this is the current conversation
            is_current = conv['id'] == st.session_state.current_thread_id
            
            # Style for current conversation
            if is_current:
                st.markdown(
                    f"""
                    <div style="
                        background-color: rgba(28, 131, 225, 0.1);
                        border-left: 3px solid #1c83e1;
                        padding: 8px;
                        margin: 2px 0;
                        border-radius: 4px;
                    ">
                        <div style="font-weight: bold; font-size: 14px; color: #1c83e1;">
                            {conv['title']}
                        </div>
                        <div style="font-size: 12px; color: #666; margin-top: 2px;">
                            {conv['updated_at']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                # Create columns for conversation item and delete button
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    if st.button(
                        conv['title'],
                        key=f"conv_{conv['id']}",
                        help=f"Created: {conv['created_at']}",
                        use_container_width=True
                    ):
                        # Save current conversation before switching
                        ConversationManager.save_current_conversation()
                        
                        # Load selected conversation
                        ConversationManager.load_conversation(conv['id'])
                        st.rerun()
                
                with col2:
                    if st.button(
                        "🗑️",
                        key=f"del_{conv['id']}",
                        help="Delete conversation",
                        use_container_width=True
                    ):
                        ConversationManager.delete_conversation(conv['id'])
                        st.rerun()

def render_user_selector():
    """Render user selector in the main header area"""
    
    # User selector in the top right
    col1, col2, col3 = st.columns([6, 2, 2])
    
    with col2:
        st.markdown("**Current User:**")
    
    with col3:
        users = ["john_doe", "jane_smith", "admin_user", "viewer_user"]
        user_labels = {
            "john_doe": "👨‍💼 John (Manager)",
            "jane_smith": "👩‍💼 Jane (Manager)", 
            "admin_user": "🔧 Admin User",
            "viewer_user": "👁️ Viewer User"
        }
        
        current_user = st.selectbox(
            "Select User",
            users,
            format_func=lambda x: user_labels.get(x, x),
            index=users.index(st.session_state.current_user),
            label_visibility="collapsed"
        )
        
        if current_user != st.session_state.current_user:
            from utils.session import SessionManager
            if SessionManager.switch_user(current_user):
                st.rerun()

def render_enhanced_chat_interface():
    """Render the enhanced chat interface with context awareness"""
    
    st.header("💬 Natural Language Business Assistant")
    
    # Context indicator  
    if st.session_state.current_thread_id:
        # Get thread title from conversations list
        user_conversations = ConversationManager.get_user_conversations(st.session_state.current_user)
        current_thread_title = "Current Thread"
        for conv in user_conversations:
            if conv['id'] == st.session_state.current_thread_id:
                current_thread_title = conv['title']
                break
        
        st.info(f"📝 **{current_thread_title}** | **Messages: {len(st.session_state.chat_history)}**")
    else:
        st.info("🆕 **New Conversation** - Start chatting to create a thread")
    
    # Sample commands
    st.markdown("""
    💡 **Sample Commands:**
    - "Filter invoices from last month"
    - "Create a ticket for system maintenance"  
    - "Show me all open tickets"
    - "Export sales data to Excel"
    """)
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your business data...")
    
    if user_input:
        # Process through backend - it will create thread automatically
        process_user_message(user_input)
        st.rerun()
    
    # Chat history display
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(f"**You** ({message['timestamp']})")
                    st.write(message["message"])
            else:
                with st.chat_message("assistant"):
                    st.write(f"**FinkraftAI** ({message['timestamp']})")
                    
                    if message.get("success", True):
                        st.write(message["message"])
                        
                        # Show trace information
                        if message.get("tool_used"):
                            st.info(f"🔧 **Tool Used:** {message['tool_used']}")
                            
                            if message.get("parameters"):
                                with st.expander("🔍 **Show Your Work** - Execution Details"):
                                    st.write("**Parameters:**")
                                    st.json(message["parameters"])
                                    
                                    trace_data = message.get("trace_data", {})
                                    if trace_data.get("confidence"):
                                        st.write(f"**Confidence:** {trace_data['confidence']}")
                                    
                                    if trace_data.get("suggestions"):
                                        st.write("**Suggestions:**")
                                        for suggestion in trace_data["suggestions"]:
                                            st.write(f"• {suggestion}")
                                    
                                    if trace_data.get("memory_context"):
                                        st.write("**Memory Context:**")
                                        st.json(trace_data["memory_context"])
                        
                        # Show data if available
                        if "data" in message and message["data"]:
                            with st.expander("📊 View Data Results"):
                                st.json(message["data"])
                    else:
                        st.error(message["message"])

def process_user_message(message: str):
    """Process user message through backend chat API"""
    import requests
    import json
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    # Add user message to chat immediately (conversational flow)
    st.session_state.chat_history.append({
        "role": "user",
        "message": message,
        "timestamp": timestamp
    })
    
    try:
        # Call backend chat API
        chat_data = {
            "user_id": st.session_state.current_user,
            "message": message,
            "session_id": st.session_state.session_id
        }
        
        response = requests.post("http://localhost:8000/chat", json=chat_data)
        
        if response.status_code == 200:
            result = response.json()
            
            # Update current thread ID if returned
            if result.get("thread_id"):
                st.session_state.current_thread_id = result["thread_id"]
            
            # Add assistant response
            st.session_state.chat_history.append({
                "role": "assistant",
                "message": result["agent_response"],
                "success": result["success"],
                "timestamp": timestamp,
                "tool_used": result.get("tool_used"),
                "parameters": result.get("parameters"),
                "trace_data": {
                    "confidence": result.get("confidence"),
                    "suggestions": result.get("suggestions", []),
                    "memory_context": result.get("memory_context", {})
                }
            })
        else:
            # Error response
            st.session_state.chat_history.append({
                "role": "assistant",
                "message": f"Service error: {response.status_code}",
                "success": False,
                "timestamp": timestamp
            })
            
    except Exception as e:
        # Connection error
        st.session_state.chat_history.append({
            "role": "assistant",
            "message": f"Connection error: {str(e)}",
            "success": False,
            "timestamp": timestamp
        })