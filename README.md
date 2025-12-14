# HelpHub - AI-Powered Support Ticket System

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.124+-green.svg)
![LangChain](https://img.shields.io/badge/LangChain-1.1+-orange.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A production-ready support ticket management system with an intelligent conversational AI agent built using **LangChain**, **LangGraph**, and **MCP (Model Context Protocol)**. Users can create, query, and manage support tickets through natural language conversations.

##  Key Features

### Intelligent AI Agent

- **Natural Language Interface**: Users interact with tickets using conversational language
- **Autonomous Tool Calling**: LangGraph-powered agent automatically selects and executes appropriate tools
- **Context-Aware Responses**: Maintains conversation history and user context
- **Role-Based Intelligence**: Agent adapts behavior based on user roles (admin vs regular user)

###  Agentic Architecture

- **MCP Integration**: Server-client separation for scalable tool orchestration
- **LangGraph State Management**: Robust state graph for multi-step reasoning
- **Dynamic Tool Selection**: Agent chooses from multiple ticket management tools
- **Async Tool Execution**: Non-blocking tool calls for optimal performance

###  Backend

- **JWT Authentication**: Secure token-based authentication with Argon2 password hashing
- **Role-Based Access Control (RBAC)**: Admin and user roles with permission management
- **SQLite Database**: Lightweight, file-based database with SQLAlchemy ORM
- **RESTful API**: Complete CRUD operations with FastAPI
- **HTMX Integration**: Dynamic, reactive frontend without heavy JavaScript

### 📊 Ticket Management

- Create, read, update, and delete tickets
- Status tracking (Open, In Progress, Resolved, Closed)
- AI and human response tracking
- User satisfaction feedback
- Advanced filtering and search

## 🏗️ Architecture

```
┌─────────────────┐
│   User/Client   │
└────────┬────────┘
         │
         │ HTTP/HTMX
         ▼
┌─────────────────────────────────┐
│      FastAPI Backend            │
│  ┌──────────────────────────┐   │
│  │  Authentication Layer    │   │
│  │  (JWT + Argon2)          │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Chat Endpoint           │   │
│  │  (Session Management)    │   │
│  └──────────────┬───────────┘   │
│                 │                │
│                 │ LLM Invocation │
│                 ▼                │
│  ┌──────────────────────────┐   │
│  │  LangGraph Agent         │   │
│  │  ┌────────────────────┐  │   │
│  │  │ State Management   │  │   │
│  │  └────────────────────┘  │   │
│  │  ┌────────────────────┐  │   │
│  │  │ Tool Node          │  │   │
│  │  │ (Conditional Edge) │  │   │
│  │  └────────────────────┘  │   │
│  └──────────┬───────────────┘   │
│             │ MCP Protocol       │
│             ▼                    │
│  ┌──────────────────────────┐   │
│  │  MCP Client              │   │
│  │  (Tool Aggregator)       │   │
│  └──────────┬───────────────┘   │
└─────────────┼───────────────────┘
              │ stdio
              ▼
┌─────────────────────────────────┐
│      MCP Server (FastMCP)       │
│  ┌──────────────────────────┐   │
│  │  create_ticket()         │   │
│  │  get_tickets()           │   │
│  │  get_ticket()            │   │
│  │  update_ticket()         │   │
│  └──────────┬───────────────┘   │
│             │                    │
│             ▼                    │
│  ┌──────────────────────────┐   │
│  │  SQLite Database         │   │
│  │  (tickets, users)        │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

## Tech Stack

### Core Framework

- **FastAPI** - High-performance async web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **SQLite** - Embedded database

### AI/ML Stack

- **LangChain** - LLM application framework
- **LangGraph** - State machine for multi-step agent workflows
- **Azure OpenAI** - GPT-4 model for natural language understanding
- **MCP (Model Context Protocol)** - Tool-calling protocol via FastMCP

### Authentication & Security

- **JWT (PyJWT)** - Token-based authentication
- **Passlib + Argon2** - Secure password hashing
- **HTTPBearer** - Bearer token security scheme

### Frontend

- **Jinja2** - Template engine
- **HTMX** - Dynamic HTML without JavaScript framework
- **Tailwind CSS** - Utility-first CSS (via CDN)

## Installation

### Prerequisites

- Python 3.10 or higher
- UV package manager (recommended) or pip
- Azure OpenAI API access

### Setup Steps

1. **Clone the repository**

```bash
git clone <your-repo-url>
cd helphub
```

2. **Install dependencies**

Using UV (recommended):

```bash
uv sync
```

Or using pip:

```bash
pip install -r requirements.txt
```

3. **Configure environment variables**

Create a `.env` file in the project root:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name
AZURE_OPENAI_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# JWT Security
JWT_SECRET_KEY=your_super_secret_key_here

# Optional: Change default admin password
# Default is admin/admin123
```

4. **⚠️ IMPORTANT: Update MCP Server Path**

Edit `mcp_cliento.py` and update the `command` path to match your Python installation:

```python
SERVERS = {
    "Tickets": {
        "transport": "stdio",
        "command": "/path/to/your/uv",  # Update this path!
        "args": [
            "run",
            "fastmcp",
            "run",
            "/absolute/path/to/helphub/mcp_srvo.py"  # Update this too!
        ]
    }
}
```

**To find your UV path:**

```bash
which uv
```

**To get absolute path to mcp_srvo.py:**

```bash
pwd  # Run this in the helphub directory
```

5. **Initialize database**

The database will be created automatically on first run with default admin user:

- Username: `admin`
- Password: `admin123`

## 🎮 Usage

### Starting the Server

```bash
# Using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or using the script
python main.py
```

The application will be available at: `http://localhost:8000`

### Default Credentials

**Admin Account:**

- Username: `admin`
- Email: `admin@system.com`
- Password: `admin123`

⚠️ **Change the admin password immediately in production!**

### API Endpoints

#### Authentication

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user info

#### Tickets

- `POST /api/tickets` - Create a ticket
- `GET /api/tickets` - List tickets (with filters)
- `GET /api/tickets/{ticket_id}` - Get specific ticket
- `PATCH /api/tickets/{ticket_id}` - Update ticket

#### Admin

- `GET /api/admin/stats` - Get system statistics (admin only)

### Chat Interface

The main feature is the AI-powered chat interface:

1. **Login/Register** at the dashboard
2. **Navigate to Dashboard** - Click "Launch Dashboard"
3. **Start Chatting** - The AI agent can help you:
   - Create tickets: _"I need help with my login issue"_
   - View tickets: _"Show me my open tickets"_
   - Get details: _"What's the status of ticket #5?"_
   - Filter tickets: _"Show resolved tickets"_

## 🧠 How the AI Agent Works

### Agent Flow

1. **User Message** → Sent to chat endpoint
2. **LangGraph Agent** → Receives message with chat history
3. **LLM Reasoning** → GPT-4 analyzes user intent
4. **Tool Selection** → Agent decides which tool(s) to use
5. **MCP Tool Execution** → Tools are called via MCP protocol
6. **Database Operations** → Tools interact with SQLite
7. **Response Formatting** → Results formatted as HTML
8. **User Receives** → Beautiful, formatted response

### Example Conversation

```
User: "Show me my open tickets"

Agent: [Analyzes intent] → [Calls get_tickets tool with status=open]
       ↓
MCP Server: [Queries database for open tickets]
       ↓
Agent: [Formats response with HTML]
       ↓
User sees: Beautifully formatted list of open tickets
```

### Available Tools

The agent has access to 4 main tools:

1. **create_ticket** - Creates new support tickets
2. **get_tickets** - Lists tickets with filtering options
3. **get_ticket** - Retrieves specific ticket details
4. **update_ticket** - Updates ticket information (role-based permissions)

## 📁 Project Structure

```
helphub/
├── main.py                 # FastAPI application & routes
├── mcp_cliento.py         # LangGraph agent & MCP client setup
├── mcp_srvo.py            # MCP server with tool definitions
├── utils.py               # Database models & utilities
├── security.py            # Password hashing configuration
├── pyproject.toml         # Project dependencies
├── .env                   # Environment variables (create this)
├── templates/             # Jinja2 HTML templates
│   ├── landing.html       # Landing page
│   ├── login.html         # Login page
│   ├── register.html      # Registration page
│   ├── dashboard.html     # Main dashboard with chat
│   └── partials/          # HTMX partial templates
│       └── chat_message.html
├── static/                # Static assets (CSS, JS, images)
└── ticketing_tool.db      # SQLite database (auto-generated)
```

## 🔑 Key Files Explained

### `main.py`

- FastAPI application setup
- Authentication endpoints (register, login)
- Ticket CRUD API endpoints
- HTMX chat endpoints
- Chat session management
- Lifespan events for agent initialization

### `mcp_cliento.py`

- LangGraph agent definition
- MCP client configuration
- State graph setup (LLM node + Tool node)
- Azure OpenAI integration
- Tool binding and execution flow

### `mcp_srvo.py`

- FastMCP server implementation
- Tool function definitions
- Database interaction layer
- HTML response formatting
- Role-based access control for tools

### `utils.py`

- Pydantic models (User, Ticket, etc.)
- Database connection management
- Database initialization
- Enums for status and roles

## 🎨 Frontend Features

- **Responsive Design**: Works on desktop and mobile
- **Real-time Updates**: HTMX for dynamic content loading
- **Beautiful UI**: Tailwind CSS styling
- **Chat Interface**: Conversational ticket management
- **Role-Based Views**: Different permissions for admin/users

## 🔒 Security Features

- **Password Hashing**: Argon2 algorithm (most secure)
- **JWT Tokens**: Secure authentication with expiry
- **Role-Based Access**: Admin vs user permissions
- **SQL Injection Protection**: SQLAlchemy parameterized queries
- **CORS Configuration**: Controlled cross-origin access

## 🚀 Deployment Tips

### For Development

```bash
uvicorn main:app --reload
```

### For Production

1. **Use a production ASGI server:**

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

2. **Set secure environment variables**
3. **Use PostgreSQL instead of SQLite** (update DATABASE_URL)
4. **Enable HTTPS**
5. **Set strong JWT_SECRET_KEY**
6. **Change default admin password**

### Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:

```bash
docker build -t helphub .
docker run -p 8000:8000 helphub
```

## 🎯 Use Cases for Upwork

This project demonstrates expertise in:

- ✅ **Agentic AI Development** - LangChain/LangGraph workflows
- ✅ **LLM Integration** - Azure OpenAI, tool calling
- ✅ **MCP Protocol** - Modern AI tool orchestration
- ✅ **Full-Stack Development** - FastAPI + HTMX
- ✅ **Authentication & Security** - JWT, RBAC
- ✅ **Database Design** - SQLAlchemy ORM
- ✅ **API Development** - RESTful endpoints
- ✅ **Async Programming** - Modern Python async/await

## 🐛 Troubleshooting

### Agent doesn't respond

- Check Azure OpenAI credentials in `.env`
- Verify MCP server paths in `mcp_cliento.py`
- Check logs for errors: `tail -f logs/app.log`

### Database errors

- Delete `ticketing_tool.db` and restart (will recreate)
- Check file permissions

### Import errors

- Run `uv sync` to install all dependencies
- Verify Python version: `python --version`

### MCP connection fails

- Ensure UV path is correct in `mcp_cliento.py`
- Check absolute path to `mcp_srvo.py`
- Run `which uv` to find UV location

## 📚 Learning Resources

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Tutorial](https://langchain-ai.github.io/langgraph/)
- [FastMCP Guide](https://github.com/jlowin/fastmcp)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [HTMX Documentation](https://htmx.org/)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

---

⭐ **If you find this project useful, please consider starring it **

---
