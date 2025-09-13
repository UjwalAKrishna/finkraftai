# FinkraftAI Streamlit Frontend - Main Application

import streamlit as st
import requests
import json
import time
from datetime import datetime
import pandas as pd

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="FinkraftAI - Unified Business Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #e0e0e0;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #2196f3;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #4caf50;
    }
    .tool-execution {
        background-color: #fff3e0;
        border: 1px solid #ff9800;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
    }
    .success-message {
        background-color: #e8f5e8;
        color: #2e7d32;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 4px solid #4caf50;
    }
    .error-message {
        background-color: #ffebee;
        color: #c62828;
        padding: 0.5rem;
        border-radius: 0.25rem;
        border-left: 4px solid #f44336;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_user' not in st.session_state:
        st.session_state.current_user = "john_doe"
    if 'user_permissions' not in st.session_state:
        st.session_state.user_permissions = []
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"streamlit_{int(time.time())}"

def make_api_call(endpoint, method="GET", data=None):
    """Make API call to backend"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=10)
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Connection error: {str(e)}"}

def load_user_permissions():
    """Load user permissions from backend"""
    result = make_api_call(f"/user/{st.session_state.current_user}/permissions")
    if result["success"]:
        st.session_state.user_permissions = result["data"].get("permissions", [])
        return result["data"]
    return None

def main():
    """Main application"""
    initialize_session_state()
    
    # Header
    st.markdown('<div class="main-header">🤖 FinkraftAI - Unified Business Assistant</div>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Control Panel")
        
        # User Selection
        st.subheader("👤 User")
        users = ["john_doe", "jane_smith", "admin_user", "viewer_user"]
        current_user = st.selectbox(
            "Select User",
            users,
            index=users.index(st.session_state.current_user)
        )
        
        if current_user != st.session_state.current_user:
            st.session_state.current_user = current_user
            st.session_state.chat_history = []  # Clear chat on user change
            st.rerun()
        
        # Load user info
        user_info = load_user_permissions()
        if user_info:
            st.success(f"**Role:** {user_info.get('groups', ['Unknown'])[0]}")
            st.info(f"**Tools:** {len(user_info.get('allowed_tools', []))}")
            st.info(f"**Permissions:** {len(st.session_state.user_permissions)}")
        
        st.divider()
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        
        if st.button("🔍 Sample: Filter Invoices", use_container_width=True):
            sample_message = "Filter invoices for last month, vendor=IndiSky, status=failed"
            process_message(sample_message)
            st.rerun()
        
        if st.button("🎫 Sample: Create Ticket", use_container_width=True):
            sample_message = "Create a ticket about failed invoices"
            process_message(sample_message)
            st.rerun()
        
        if st.button("📊 Sample: View Tickets", use_container_width=True):
            sample_message = "Show my tickets"
            process_message(sample_message)
            st.rerun()
        
        st.divider()
        
        # System Status
        st.subheader("🏥 System Health")
        health_check = make_api_call("/")
        if health_check["success"]:
            st.success("✅ Backend Online")
        else:
            st.error("❌ Backend Offline")
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat Assistant", "📊 Dashboard", "🎫 Tickets", "👤 Admin"])
    
    with tab1:
        render_chat_interface()
    
    with tab2:
        render_dashboard()
    
    with tab3:
        render_ticket_management()
    
    with tab4:
        render_admin_panel()

def process_message(message):
    """Process user message through the backend"""
    
    # Add user message to chat
    st.session_state.chat_history.append({
        "role": "user",
        "message": message,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })
    
    # Try direct tool execution for reliable demo
    if "filter" in message.lower() and "invoice" in message.lower():
        # Direct filter tool execution
        tool_data = {
            "user_id": st.session_state.current_user,
            "tool_name": "filter_data",
            "params": {
                "dataset": "invoices",
                "period": "last month",
                "vendor": "IndiSky" if "indisky" in message.lower() else None,
                "status": "failed" if "failed" in message.lower() else None
            }
        }
        result = make_api_call("/execute_tool", "POST", tool_data)
    
    elif "ticket" in message.lower() and "create" in message.lower():
        # Create ticket
        ticket_data = {
            "user_id": st.session_state.current_user,
            "title": "Invoice Investigation Ticket",
            "description": "Created from chat: " + message,
            "priority": "high"
        }
        result = make_api_call("/tickets/create", "POST", ticket_data)
    
    elif "show" in message.lower() and "ticket" in message.lower():
        # View tickets
        result = make_api_call(f"/tickets/{st.session_state.current_user}")
    
    else:
        # Try chat endpoint (may fail due to LLM quota)
        chat_data = {
            "user_id": st.session_state.current_user,
            "message": message,
            "session_id": st.session_state.session_id
        }
        result = make_api_call("/chat", "POST", chat_data)
    
    if result["success"]:
        response_data = result["data"]
        
        # Add assistant response
        st.session_state.chat_history.append({
            "role": "assistant",
            "message": format_response(response_data),
            "success": True,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "data": response_data
        })
    else:
        st.session_state.chat_history.append({
            "role": "assistant",
            "message": f"Service error: {result.get('error', 'Unknown error')}",
            "success": False,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })

def format_response(data):
    """Format API response for display"""
    if "message" in data:
        return data["message"]
    elif "ticket" in data:
        ticket = data["ticket"]
        return f"✅ Created ticket {ticket['id']}: {ticket['title']}"
    elif "tickets" in data:
        tickets_data = data["tickets"]
        if isinstance(tickets_data, dict) and "tickets" in tickets_data:
            tickets = tickets_data["tickets"]
            if tickets:
                return f"📋 Found {len(tickets)} tickets:\n" + "\n".join([f"• {t['id']}: {t['title']} ({t['status']})" for t in tickets[:5]])
            else:
                return "📋 No tickets found"
        return f"📋 Tickets: {str(tickets_data)}"
    elif "data" in data:
        tool_data = data["data"]
        if "filtered_records" in tool_data:
            count = tool_data["filtered_records"]
            return f"🔍 Found {count} records matching your criteria"
        return f"✅ Tool executed successfully: {data.get('message', 'Done')}"
    else:
        return f"✅ {data.get('message', 'Operation completed')}"

def render_chat_interface():
    """Render the main chat interface"""
    st.header("💬 Natural Language Business Assistant")
    
    st.info("💡 **Sample Commands:**\n"
            "• 'Filter invoices for last month, vendor=IndiSky, status=failed'\n"
            "• 'Create a ticket about failed invoices'\n"
            "• 'Show my tickets'")
    
    # Chat input
    user_input = st.chat_input("Ask me anything about your business data...")
    
    if user_input:
        process_message(user_input)
        st.rerun()
    
    # Display chat history
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                with st.chat_message("user"):
                    st.write(f"**You** ({message['timestamp']})")
                    st.write(message["message"])
            
            else:  # assistant
                with st.chat_message("assistant"):
                    st.write(f"**FinkraftAI** ({message['timestamp']})")
                    
                    if message.get("success"):
                        st.success(message["message"])
                        
                        # Show data if available
                        if message.get("data"):
                            with st.expander("📊 View Details"):
                                st.json(message["data"])
                    else:
                        st.error(message["message"])

def render_dashboard():
    """Render dashboard with system stats"""
    st.header("📊 System Dashboard")
    
    # System stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("👤 Current User", st.session_state.current_user)
    
    with col2:
        st.metric("🔧 Available Tools", len(st.session_state.user_permissions))
    
    with col3:
        st.metric("💬 Chat Messages", len(st.session_state.chat_history))
    
    with col4:
        health = make_api_call("/")
        status = "🟢 Online" if health["success"] else "🔴 Offline"
        st.metric("🏥 Backend Status", status)
    
    st.divider()
    
    # User permissions
    st.subheader("🔐 Your Permissions")
    if st.session_state.user_permissions:
        permission_df = pd.DataFrame({
            "Tool/Permission": st.session_state.user_permissions,
            "Status": ["✅ Allowed"] * len(st.session_state.user_permissions)
        })
        st.dataframe(permission_df, use_container_width=True)
    else:
        st.warning("No permissions loaded. Check backend connection.")

def render_ticket_management():
    """Render ticket management interface"""
    st.header("🎫 Ticket Management")
    
    # Get user tickets
    tickets_result = make_api_call(f"/tickets/{st.session_state.current_user}")
    
    if tickets_result["success"]:
        tickets_data = tickets_result["data"]
        
        if "tickets" in tickets_data and isinstance(tickets_data["tickets"], dict):
            tickets = tickets_data["tickets"].get("tickets", [])
            
            if tickets:
                # Display tickets
                st.success(f"Found {len(tickets)} tickets")
                
                for ticket in tickets:
                    with st.expander(f"🎫 {ticket['id']}: {ticket['title']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Status:** {ticket['status']}")
                            st.write(f"**Priority:** {ticket['priority']}")
                        with col2:
                            st.write(f"**Created:** {ticket['created_at']}")
                            st.write(f"**Assigned:** {ticket.get('assigned_to', 'Unassigned')}")
                        
                        st.write(f"**Description:** {ticket['description']}")
            else:
                st.info("No tickets found. Create one using the chat interface!")
        else:
            st.warning("Unexpected ticket data format")
    else:
        st.error("Failed to load tickets")
    
    st.divider()
    
    # Quick ticket creation
    st.subheader("➕ Quick Create Ticket")
    with st.form("create_ticket"):
        title = st.text_input("Ticket Title")
        description = st.text_area("Description")
        priority = st.selectbox("Priority", ["low", "medium", "high"])
        
        if st.form_submit_button("Create Ticket"):
            if title and description:
                ticket_data = {
                    "user_id": st.session_state.current_user,
                    "title": title,
                    "description": description,
                    "priority": priority
                }
                result = make_api_call("/tickets/create", "POST", ticket_data)
                
                if result["success"]:
                    st.success("Ticket created successfully!")
                    st.rerun()
                else:
                    st.error(f"Failed to create ticket: {result.get('error')}")
            else:
                st.error("Please fill in all fields")

def render_admin_panel():
    """Render admin panel (if user has admin access)"""
    st.header("👤 Administration")
    
    if st.session_state.current_user == "admin_user":
        st.success("🔐 Admin access granted")
        
        # System statistics
        st.subheader("📊 System Statistics")
        
        # Mock stats for now - in production would call admin API
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Users", "4")
            st.metric("Active Sessions", "1")
        
        with col2:
            st.metric("Total Tickets", "15")
            st.metric("Failed Operations", "2")
        
        with col3:
            st.metric("API Calls Today", "47")
            st.metric("Memory Usage", "85%")
        
        # User management
        st.subheader("👥 User Management")
        users_df = pd.DataFrame({
            "User ID": ["john_doe", "jane_smith", "admin_user", "viewer_user"],
            "Role": ["Manager", "Manager", "Admin", "Viewer"],
            "Status": ["🟢 Active", "🟢 Active", "🟢 Active", "🟢 Active"],
            "Last Seen": ["Now", "1h ago", "Now", "2d ago"]
        })
        st.dataframe(users_df, use_container_width=True)
        
    else:
        st.warning("🔒 Admin access required. Switch to 'admin_user' to view admin features.")

if __name__ == "__main__":
    main()