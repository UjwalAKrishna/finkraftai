
# Quick Overview

## Proposed Solution - An AI agent with tool calling support and reasoning with A Good Memory Manager
# FinkraftAI Implementation Approach

## Problem vs Solution Comparison

| **Problem Statement**              | **Our Implementation**                                              |
| ---------------------------------- | ------------------------------------------------------------------- |
| **"I just say it, it happens"**    | **LLM Agent + Tool Registry**                                       |
| Ask for actions in simple language | Natural language → Tool execution via LLM decisions                 |
|                                    | `"Filter invoices last month"` → `filter_data` tool with parameters |
| **"Don't make me repeat myself"**  | **Memory Manager + Conversation Threads**                           |
| Context continues across sessions  | Database stores conversation history, retrieves context             |
|                                    | `"Why did these fail?"` understands "these" from previous filter    |
| **"Explain it simply"**            | **Natural Language Generation**                                     |
| Clear, short answers               | LLM crafts conversational responses from tool results               |
|                                    | `"5 invoices failed due to missing GSTIN information"`              |
| **"Show your work"**               | **Trace System + UI Dropdown**                                      |
| See what exactly ran               | Every tool execution logged with timing and parameters              |
|                                    | Expandable trace viewer in frontend                                 |
| **"Only what I should see"**       | **Role-Based Access Control**                                       |
| Role governs visibility            | Permission validation before tool execution                         |
|                                    | Admin/Manager/Viewer roles with different tool access               |

## Sample Scenario Implementation

**PRD**: `"Filter invoices for last month, vendor='IndiSky', status=failed"` → `"Why did these fail?"` → `"Create a ticket"`

**Our System**:
1. **Filter request** → LLM extracts parameters → `filter_data` tool → Stores context
2. **"Why failed?"** → Memory retrieves context → Analyzes previous results → Explains failures  
3. **"Create ticket"** → Uses context from conversation → `create_ticket` tool
4. **Next day** → Conversation thread persists → Context available

## Technical Architecture

```
User Input → Memory Manager → LLM Agent → Tool Execution → Response + Memory Storage
              ↑                                                      ↓
           Conversation                                         Context for
           Context                                             Next Request
```

**Key Components**:
- `memory_manager.py` - Conversation persistence
- `memory_aware_agent.py` - LLM + context integration  
- `trace_service.py` - Execution transparency
- `permission_repo.py` - Role-based access
- Frontend chat UI - Natural language first, trace dropdown