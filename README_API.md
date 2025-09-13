# FinkraftAI API with Gemini LLM

## Quick Start

```bash
# Start the backend server
python3 run_app.py
```

The server will start at `http://localhost:8000` with automatic API documentation at `http://localhost:8000/docs`.

## 🤖 AI Agent Features

- **Gemini 1.5 Flash LLM** - Advanced natural language understanding
- **Proper Agent Pattern** - Planning → Execution → Response Generation
- **Smart tool selection** - AI reasons about which tool to use
- **Dynamic parameter extraction** - Extracts entities from natural language
- **Contextual responses** - LLM generates responses based on actual tool results

## Available Endpoints

### Health Check
```
GET /
```

### Chat with AI Agent (Gemini LLM)
```
POST /chat
{
  "user_id": "john_doe",
  "message": "filter invoices for last month, vendor='IndiSky', status=failed"
}

Response:
{
  "agent_response": "Great! I've filtered your invoices for last month, looking specifically for those from IndiSky with a 'failed' status.\n\nI found 7 invoices that match your criteria out of a total of 124 invoices from last month. Here's a snippet of the data: The first three invoices show amounts of $1500, $2300, and $980 respectively.",
  "success": true,
  "tool_used": "filter_data", 
  "parameters": {"dataset": "invoices", "period": "last month", "vendor": "IndiSky", "status": "failed"},
  "planning": {"reasoning": "The user explicitly requests to filter invoices based on specific criteria..."}
}
```

### User Permissions
```
GET /user/{user_id}/permissions
GET /user/{user_id}/tools
```

### Direct Tool Execution
```
POST /execute_tool
{
  "user_id": "john_doe",
  "tool_name": "filter_data", 
  "params": {
    "dataset": "invoices",
    "period": "last month",
    "vendor": "IndiSky"
  }
}
```

### Tickets
```
POST /tickets/create
GET /tickets/{user_id}
PUT /tickets/update
```

## Sample Users

- **admin_user** - Full access (Admin role)
- **john_doe** - Manager access (can create/manage tickets)
- **jane_smith** - Manager access
- **viewer_user** - Read-only access (Viewer role)

## Available Tools

- `filter_data` - Filter datasets by criteria
- `export_report` - Export data as CSV/Excel
- `create_ticket` - Create support tickets
- `view_tickets` - View user's tickets
- `update_ticket` - Update/assign/close tickets

## Example API Calls

### Natural Language Chat (Recommended)
```bash
# Chat with agent using natural language
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"john_doe","message":"filter invoices for last month, vendor=IndiSky, status=failed"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"john_doe","message":"create ticket: Failed invoices need GSTIN fix"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"john_doe","message":"show my tickets"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"john_doe","message":"download the report"}'
```

### Direct API Calls
```bash
# Get user permissions
curl http://localhost:8000/user/john_doe/permissions

# Filter data directly
curl -X POST http://localhost:8000/execute_tool \
  -H "Content-Type: application/json" \
  -d '{"user_id":"john_doe","tool_name":"filter_data","params":{"dataset":"invoices","period":"last month"}}'

# Create ticket directly
curl -X POST http://localhost:8000/tickets/create \
  -H "Content-Type: application/json" \
  -d '{"user_id":"john_doe","title":"Test Ticket","description":"API test"}'
```

## Natural Language Examples

The AI agent understands these types of requests:

**Filter Data:**
- "filter invoices for last month"
- "show sales for last week"
- "find IndiSky invoices with failed status"

**Export Reports:**
- "export data as CSV"
- "download the report"
- "export data as Excel"

**Ticket Management:**
- "create ticket: System issue description"
- "show my tickets"
- "close ticket TIC-0001"
- "assign TIC-0002 to dev_team"