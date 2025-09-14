# Chat interface component - Fixed UX Version
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
    """Render the enhanced chat interface with ChatGPT-like UX"""
    
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
    
    # Create a scrollable message area
    message_container = st.container()
    
    with message_container:
        if st.session_state.chat_history:
            # Display messages in chronological order (oldest first, newest last)
            for message in st.session_state.chat_history:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(f"**You** ({message['timestamp']})")
                        st.write(message["message"])
                else:
                    with st.chat_message("assistant"):
                        st.write(f"**FinkraftAI** ({message['timestamp']})")
                        
                        if message.get("success", True):
                            # PRIMARY: Natural language response prominently displayed
                            st.markdown(f"**{message['message']}**")
                            
                            # CONTEXT CONTINUITY: Show suggestions for next actions (key PRD requirement)
                            response_data = message.get("data", {})
                            suggestions = response_data.get("suggestions", [])
                            
                            if suggestions:
                                st.info("💡 **What you can do next:**")
                                cols = st.columns(min(len(suggestions), 3))
                                for i, suggestion in enumerate(suggestions[:3]):
                                    with cols[i]:
                                        if st.button(f"📋 {suggestion}", key=f"suggestion_{message.get('timestamp', '')}_{i}", use_container_width=True):
                                            process_user_message(suggestion)
                                            st.rerun()
                            
                            # SECONDARY: Trace details in collapsible section (optional viewing)
                            tool_used = message.get("tool_used")
                            
                            # Only show trace dropdown if there's technical information available
                            show_trace = (tool_used and tool_used != "llm_only") or response_data.get("trace_summary")
                            
                            if show_trace:
                                with st.expander("🔍 **Show Details** - Execution Trace"):
                                    # Tool execution info
                                    if tool_used:
                                        st.write(f"**🔧 Tools Used:** {tool_used}")
                                    
                                    # Execution summary from new system
                                    if response_data.get("trace_summary"):
                                        st.write("**📋 Execution Summary:**")
                                        st.text(response_data["trace_summary"])
                                    
                                    # Detailed trace information
                                    if response_data.get("trace_details"):
                                        st.write("**🕰️ Detailed Trace:**")
                                        trace_details = response_data["trace_details"]
                                        
                                        if trace_details.get("tool_calls"):
                                            for i, tool_call in enumerate(trace_details["tool_calls"], 1):
                                                st.write(f"**Step {i}:** {tool_call.get('tool_name', 'Unknown')}")
                                                if tool_call.get("parameters"):
                                                    st.json(tool_call["parameters"])
                                                if tool_call.get("execution_time_ms"):
                                                    st.write(f"⏱️ Execution time: {tool_call['execution_time_ms']}ms")
                                                st.divider()
                                    
                                    # Plan summary if available
                                    if response_data.get("plan_summary"):
                                        plan = response_data["plan_summary"]
                                        st.write("**🎯 Plan Summary:**")
                                        st.write(f"• Goal: {plan.get('goal', 'N/A')}")
                                        st.write(f"• Steps: {plan.get('completed_steps', 0)}/{plan.get('total_steps', 0)}")
                                        st.write(f"• Time: {plan.get('execution_time_ms', 0)}ms")
                                    
                                    # Raw data for power users
                                    if response_data and len(str(response_data)) > 50:
                                        with st.expander("🔬 **Raw Data** (Advanced)"):
                                            st.json(response_data)
                        else:
                            st.error(message["message"])
        else:
            # Empty state - welcome message
            st.markdown("""
            <div style="text-align: center; padding: 50px; color: #666;">
                <h3>👋 Welcome to FinkraftAI!</h3>
                <p>Start a conversation by typing a message below.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Show sample commands as clickable buttons when no messages
            st.markdown("**💡 Try these commands:**")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔍 Filter invoices from last month", use_container_width=True):
                    process_user_message("Filter invoices from last month")
                    st.rerun()
                if st.button("📊 Show me all tickets", use_container_width=True):
                    process_user_message("Show me all tickets")
                    st.rerun()
            with col2:
                if st.button("🎫 Create a maintenance ticket", use_container_width=True):
                    process_user_message("Create a ticket for system maintenance")
                    st.rerun()
                if st.button("📋 Export sales data", use_container_width=True):
                    process_user_message("Export sales data to Excel")
                    st.rerun()
    
    # CRITICAL UX FIX: Chat input at BOTTOM (like ChatGPT)
    user_input = st.chat_input("Ask me anything about your business data...")
    
    if user_input:
        # Process through backend - it will create thread automatically
        process_user_message(user_input)
        st.rerun()

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
            
            # Add assistant response with enhanced trace information and suggestions
            st.session_state.chat_history.append({
                "role": "assistant",
                "message": result["agent_response"],
                "success": result["success"],
                "timestamp": timestamp,
                "tool_used": result.get("tool_used"),
                "data": {
                    "trace_summary": result.get("trace_summary"),
                    "trace_details": result.get("trace_details"),
                    "plan_summary": result.get("plan_summary"),
                    "execution_details": result.get("execution_details"),
                    "suggestions": result.get("suggestions", []),
                    "analysis": result.get("analysis", ""),
                    "show_traces": result.get("show_traces", False)
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