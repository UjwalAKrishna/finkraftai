# FinkraftAI - Unified In-App Assistant

A conversational AI assistant that allows customers to interact with business systems through natural language. Execute actions, get explanations, and manage support tickets with conversation continuity across sessions.

## 🎥 Demo Video

**Watch the complete explanation and demo**: [🎬 Demo Video](https://drive.google.com/file/d/1Lr7X7EaqNXgY9N5f4fnMAjJXXBAQmK1r/view?usp=sharing)

This video demonstrates the full system capabilities, conversation continuity, and all PRD requirements in action.

## 🎯 Project Overview

FinkraftAI transforms customer interaction from discrete tool usage to **conversational business workflow management**. Customers can say "filter invoices from last month" or "why did these fail?" and get intelligent responses with full context awareness.

### Key Features

- **Natural Language Actions**: "Filter invoices for last month" → Direct execution
- **Conversation Continuity**: "Why did these fail?" understands previous context
- **Memory Across Sessions**: Tomorrow feels like yesterday never ended
- **Role-Based Access**: Different permissions for Admin/Manager/Viewer
- **Transparent Execution**: See exactly what tools ran and why
- **Support Integration**: Create and track tickets from conversations

## 🏗️ Architecture

```
Frontend (Streamlit) ←→ Backend (FastAPI) ←→ Database (SQLite)
                                ↓
                        LLM Provider (Gemini)
                                ↓
                    Business Tools (Filter, Export, Tickets)
```

### Core Components

- **Memory-Aware Agent**: Maintains conversation context and continuity
- **Tool Registry**: 5 business tools (filter_data, create_ticket, export_report, view_tickets, update_ticket)
- **Trace System**: Complete execution transparency
- **Permission System**: Role-based access control
- **LLM Integration**: Gemini for natural language understanding

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Gemini API key
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd finkraftai
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file in root directory
echo "GEMINI_API_KEY=your_gemini_api_key_here" > .env
```

4. **Initialize the database**
```bash
python database/init_db.py
```

5. **Start the backend server**
```bash
python run_app.py
```

6. **Start the frontend (in a new terminal)**
```bash
cd frontend
streamlit run app.py
```

7. **Access the application**
- Frontend: http://localhost:8501
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## 🔧 Deployment Instructions

### Environment Setup

1. **Get Gemini API Key**
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create a new API key
   - Copy the key for configuration

2. **Configure Environment**
```bash
# Production .env file
GEMINI_API_KEY=your_actual_gemini_api_key
DATABASE_URL=sqlite:///production.db
LOG_LEVEL=INFO
```

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export GEMINI_API_KEY="your_gemini_api_key"

# 3. Initialize database
python database/init_db.py

# 4. Run backend
python run_app.py &

# 5. Run frontend
cd frontend && streamlit run app.py
```

### Docker Deployment

```bash
# Build and run with Docker
docker-compose up --build

# Or run individually
docker build -t finkraftai-backend .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key finkraftai-backend
```

### Production Deployment

1. **Backend (FastAPI)**
```bash
# Using gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker backend.main:app

# Using uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4
```

2. **Frontend (Streamlit)**
```bash
# Production Streamlit
streamlit run frontend/app.py --server.port 8501 --server.address 0.0.0.0
```

3. **Environment Variables**
```bash
# Required for production
GEMINI_API_KEY=your_production_gemini_key
DATABASE_URL=your_production_database_url
CORS_ORIGINS=["https://your-frontend-domain.com"]
LOG_LEVEL=INFO
```

## 📊 Sample Usage

### Basic Conversation Flow

```
User: "Filter invoices for last month, vendor=IndiSky, status=failed"
AI: "I found 2 failed invoices from IndiSky for last month."

User: "Why did these fail?"
AI: "5 invoices failed due to missing GSTIN information. I recommend contacting IndiSky to provide their GSTIN details."

User: "Create a ticket for this issue"
AI: "Created ticket TIC-007 for IndiSky GSTIN issues. You'll be notified when it's resolved."
```

### Role-Based Access

- **Admin**: Can filter data, create tickets, export reports, manage all tickets
- **Manager**: Can filter data, create tickets, view own tickets  
- **Viewer**: Can only view tickets

## 🛠️ Development

### Project Structure

```
finkraftai/
├── backend/
│   ├── core/           # Core AI agent and memory system
│   ├── tools/          # Business tool implementations
│   ├── services/       # Supporting services (trace, conversation)
│   └── main.py         # FastAPI application
├── frontend/
│   ├── components/     # Streamlit UI components
│   ├── utils/          # Frontend utilities
│   └── app.py          # Main Streamlit app
├── database/
│   ├── migrations/     # Database schema
│   └── repositories/   # Data access layer
├── external_db/        # Sample business data
├── case-study/         # Documentation and analysis
└── config/             # Configuration files
```

### Key Files

- `backend/core/memory_aware_agent.py` - Main AI agent with conversation memory
- `backend/core/memory_manager.py` - Conversation persistence and context
- `backend/tools/` - Business action implementations
- `frontend/components/chat_ui.py` - Chat interface with trace viewer
- `database/migrations/001_initial_schema.sql` - Database schema

### Adding New Tools

1. Create tool class in `backend/tools/`
2. Register in `backend/core/tool_registry.py`
3. Add permissions in `database/repositories/permission_repo.py`
4. Update frontend suggestions in `frontend/components/chat_ui.py`

### API Endpoints

- `POST /chat` - Main conversation endpoint
- `GET /memory/{user_id}/insights` - User memory insights
- `POST /execute_tool` - Direct tool execution
- `GET /tickets/{user_id}` - User tickets
- `POST /tickets/create` - Create new ticket

## 🧪 Testing

### Run Tests

```bash
# Backend tests
python -m pytest backend/tests/

# Integration tests
python -m pytest tests/integration/

# Memory system tests
python -c "from backend.core.memory_manager import memory_manager; print('Memory system working!')"
```

### Sample Test Scenarios

```bash
# Test conversation continuity
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "Filter invoices for last month"}'

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "message": "Why did these fail?"}'
```

## 📚 Documentation

### Detailed Documentation

For comprehensive technical details, see the `case-study/` folder:

- **`TECHNICAL_ARCHITECTURE.md`** - Complete system architecture, database schema, API specifications
- **`IMPLEMENTATION_APPROACH.md`** - Problem-solution mapping and technical decisions
- **`LLM_OPTIMIZATION_SUMMARY.md`** - LLM usage optimization strategies
- **`sample_scenario.md`** - Complete user journey examples

### API Documentation

- Interactive API docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

## 🔍 Troubleshooting

### Common Issues

1. **Gemini API Key Issues**
```bash
# Check if key is set
echo $GEMINI_API_KEY

# Test API connection
curl -H "Authorization: Bearer $GEMINI_API_KEY" \
  "https://generativelanguage.googleapis.com/v1/models"
```

2. **Database Connection Issues**
```bash
# Reinitialize database
python database/init_db.py

# Check database tables
sqlite3 conversations.db ".tables"
```

3. **Memory System Issues**
```bash
# Test memory system
python -c "
from backend.core.memory_manager import memory_manager
print('Memory test:', memory_manager.get_active_thread('test_user'))
"
```

4. **Frontend Connection Issues**
- Ensure backend is running on port 8000
- Check CORS settings in `backend/main.py`
- Verify Streamlit can reach backend API

### Logs and Debugging

```bash
# Backend logs
tail -f logs/backend.log

# Enable debug mode
export LOG_LEVEL=DEBUG
python run_app.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-tool`)
3. Commit changes (`git commit -am 'Add new business tool'`)
4. Push to branch (`git push origin feature/new-tool`)
5. Create Pull Request

### Development Guidelines

- Follow Python PEP 8 style guide
- Add tests for new features
- Update documentation for API changes
- Ensure conversation continuity works with new tools

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋‍♂️ Support

For issues and questions:
- Check the `case-study/` documentation first
- Create an issue in the repository
- Review API documentation at http://localhost:8000/docs

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Voice interface integration
- [ ] Advanced analytics dashboard
- [ ] Webhook integrations
- [ ] Mobile app development
- [ ] Enterprise SSO integration