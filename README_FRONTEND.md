# FinkraftAI Frontend

## 🚀 Quick Start

### Start Backend (Terminal 1)
```bash
python3 run_app.py
```
Backend will run on: http://localhost:8000

### Start Frontend (Terminal 2)
```bash
cd frontend
python3 run_frontend.py
```
Frontend will run on: http://localhost:8501

## 🎯 Features

### 💬 Chat Interface
- **Natural Language Commands**: Just type what you want
- **Sample Commands Available**:
  - "Filter invoices for last month, vendor=IndiSky, status=failed"
  - "Create a ticket about failed invoices"
  - "Show my tickets"

### 🔐 Role-Based Access
- **Switch Between Users**: john_doe, jane_smith, admin_user, viewer_user
- **Different Permissions**: Tools available based on user role
- **Real-Time Role Info**: See your permissions in sidebar

### 📊 Dashboard
- **System Health**: Backend status monitoring
- **User Stats**: Current user, available tools, chat history
- **Permission Matrix**: View your allowed tools/permissions

### 🎫 Ticket Management
- **View All Tickets**: See your existing tickets
- **Quick Create**: Fast ticket creation form
- **Ticket Details**: Full ticket information with status

### 👤 Admin Panel
- **System Statistics**: Users, sessions, API calls
- **User Management**: View all users and their roles
- **Admin Access**: Only available to admin_user

## 🎨 User Interface

### Sidebar Controls
- **User Switcher**: Change active user to test different roles
- **Quick Actions**: Pre-built sample commands
- **System Status**: Real-time backend health check

### Main Tabs
1. **💬 Chat Assistant**: Natural language interface
2. **📊 Dashboard**: System overview and stats
3. **🎫 Tickets**: Ticket management interface
4. **👤 Admin**: Administration panel (admin only)

## 🧪 Testing the System

### Sample Workflow
1. **Start as john_doe (Manager role)**
2. **Click "Sample: Filter Invoices"** → See real IndiSky failed invoices
3. **Click "Sample: Create Ticket"** → Create support ticket
4. **Click "Sample: View Tickets"** → See your tickets
5. **Switch to admin_user** → Access admin features
6. **Switch to viewer_user** → See restricted access

### Manual Commands
Type these in the chat:
- `Filter invoices for last month, vendor=IndiSky, status=failed`
- `Create a ticket about GSTIN issues`
- `Show my tickets`
- `Export the filtered data`

## 🔧 Technical Details

### Frontend Stack
- **Streamlit**: Web framework for rapid development
- **Requests**: HTTP client for backend API calls
- **Pandas**: Data manipulation and display

### API Integration
- **REST API Calls**: Direct integration with backend endpoints
- **Fallback Logic**: Graceful handling when LLM is unavailable
- **Real-Time Updates**: Live data from backend database

### Responsive Design
- **Multi-column Layout**: Optimized for different screen sizes
- **Custom CSS**: Professional styling and user experience
- **Interactive Elements**: Real-time updates and feedback

## 🎯 Demo Scenarios

### Business User Scenario
1. Filter failed invoices to investigate issues
2. Understand why invoices failed (GSTIN problems)
3. Create tickets to track resolution
4. Monitor ticket status and progress

### Admin Scenario
1. Switch to admin_user
2. View system statistics and user activity
3. Monitor backend health and performance
4. Manage user permissions and access

### Cross-Role Testing
1. Test same commands with different users
2. See how permissions restrict access
3. Verify role-based functionality

## 🚀 Production Ready

The frontend provides:
- ✅ **Complete UI**: All backend features accessible
- ✅ **Role-Based UX**: Different experiences per user type
- ✅ **Real Data**: Shows actual business data from backend
- ✅ **Professional Design**: Clean, modern interface
- ✅ **Responsive Layout**: Works on different screen sizes
- ✅ **Error Handling**: Graceful fallbacks when services unavailable

**Ready for business users!** 🎯