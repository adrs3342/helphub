from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, HTTPException, Form, Depends, status, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, timedelta, timezone
import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from enum import Enum
from contextlib import contextmanager, asynccontextmanager
import uvicorn
import hashlib
import secrets
import jwt
from passlib.context import CryptContext
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError
import logging
from dotenv import load_dotenv
from utils import *
from mcp_cliento import *
load_dotenv()
import asyncio
from security import *
# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "raurrr")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing

security = HTTPBearer()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store chat sessions in memory (use Redis in production)
chat_sessions = {}


## agent initialization
# agent_instance = asyncio.run(agent())

# async def tool_llm(msg):
#     state = {"messages": msg}

#     resp = await agent_instance.ainvoke(state)
#     answer = resp["messages"][-1]
#     return msg.append(answer)


agent_instance = None
tool_llm = None


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        global agent_instance, tool_llm
        agent_instance = await agent()   # initialize your async LangGraph graph

    # Define tool_llm NOW that agent_instance exists
        async def tool_llm(msg: list):
            state = {"messages": msg}
            resp = await agent_instance.ainvoke(state)
            msg.append(resp["messages"][-1])
            return msg
        initialize_database_and_tables()

        logger.info("Application startup complete")
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Application shutting down")

# App creation with lifespan
app = FastAPI(
    title="ISTM - Incident Management System",
    lifespan=lifespan
)

# Templates setup
templates = Jinja2Templates(directory="templates")

# Enable CORS Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except RuntimeError:
    pass  # Directory doesn't exist yet

# Authentication functions
def verify_password(plain_password, hashed_password):
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False

def get_password_hash(password):
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise HTTPException(status_code=500, detail="Error processing password")

def get_user(username: str):
    try:
        with get_db() as db:
            result = db.execute(text("SELECT * FROM users WHERE username = :username"), {"username": username})
            user = result.fetchone()
            if user:
                return {
                    "id": user[0],
                    "username": user[1],
                    "email": user[2],
                    "full_name": user[3],
                    "hashed_password": user[4],
                    "role": user[5],
                    "is_active": user[6]
                }
            return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user['hashed_password']):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except jwt.PyJWTError:
        raise credentials_exception
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

def get_user_from_token(token: str):
    """Helper to get user from token string"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return get_user(username=username)
    except jwt.PyJWTError:
        return None

async def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# ============================================================================
# RESPONSE FORMATTER HELPERS
# ============================================================================

def format_ticket_details(ticket_data: dict) -> str:
    """Format a single ticket into nice HTML"""
    status_colors = {
        "open": "bg-green-100 text-green-800",
        "in_progress": "bg-blue-100 text-blue-800",
        "resolved": "bg-purple-100 text-purple-800",
        "closed": "bg-gray-100 text-gray-800"
    }
    
    status = ticket_data.get('status', 'unknown')
    status_class = status_colors.get(status, 'bg-gray-100 text-gray-800')
    
    html = f"""
    <div class="ticket-card bg-white border border-gray-200 rounded-lg p-4 my-2">
        <div class="flex items-center justify-between mb-3">
            <h3 class="text-lg font-semibold text-gray-800">Ticket #{ticket_data['id']}</h3>
            <span class="inline-block px-3 py-1 text-xs font-medium rounded-full {status_class}">
                {status.upper().replace('_', ' ')}
            </span>
        </div>
        
        <div class="space-y-2 text-sm">
            <div>
                <span class="font-medium text-gray-600">Query:</span>
                <p class="text-gray-800 mt-1">{ticket_data['query']}</p>
            </div>
    """
    
    if ticket_data.get('llm_response'):
        html += f"""
            <div class="mt-3 p-3 bg-blue-50 rounded">
                <span class="font-medium text-blue-800">AI Response:</span>
                <p class="text-gray-700 mt-1">{ticket_data['llm_response']}</p>
            </div>
        """
    
    if ticket_data.get('final_response'):
        html += f"""
            <div class="mt-3 p-3 bg-green-50 rounded">
                <span class="font-medium text-green-800">Final Response:</span>
                <p class="text-gray-700 mt-1">{ticket_data['final_response']}</p>
            </div>
        """
    
    if ticket_data.get('responded_by') and ticket_data['responded_by'] != 'none':
        html += f"""
            <div class="text-xs text-gray-500 mt-2">
                <span class="font-medium">Handled by:</span> {ticket_data['responded_by'].upper()}
            </div>
        """
    
    if ticket_data.get('is_resolved'):
        html += f"""
            <div class="mt-2 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-800">
                âœ“ This ticket has been resolved
            </div>
        """
    
    if ticket_data.get('user_satisfied') is not None:
        satisfaction = "ðŸ˜Š Satisfied" if ticket_data['user_satisfied'] else "ðŸ˜ž Not Satisfied"
        html += f"""
            <div class="text-xs text-gray-600 mt-2">
                <span class="font-medium">User Feedback:</span> {satisfaction}
            </div>
        """
    
    html += f"""
            <div class="text-xs text-gray-400 mt-3 flex justify-between">
                <span>Created: {ticket_data.get('created_at', 'N/A')}</span>
                <span>Updated: {ticket_data.get('updated_at', 'N/A')}</span>
            </div>
        </div>
    </div>
    """
    
    return html


def format_ticket_list(tickets: list, title: str = "Your Tickets") -> str:
    """Format a list of tickets into nice HTML"""
    if not tickets:
        return f"<p class='text-gray-600'>ðŸ“­ No tickets found matching your criteria.</p>"
    
    status_colors = {
        "open": "bg-green-100 text-green-800",
        "in_progress": "bg-blue-100 text-blue-800",
        "resolved": "bg-purple-100 text-purple-800",
        "closed": "bg-gray-100 text-gray-800"
    }
    
    count = len(tickets)
    html = f"""
    <div class="mb-4">
        <h3 class="text-lg font-semibold text-gray-800 mb-3">{title} ({count} ticket{'s' if count != 1 else ''})</h3>
        <div class="space-y-2">
    """
    
    for ticket in tickets:
        status = ticket.get('status', 'unknown')
        status_class = status_colors.get(status, 'bg-gray-100 text-gray-800')
        query_preview = ticket['query'][:80] + ('...' if len(ticket['query']) > 80 else '')
        
        resolved_badge = ""
        if ticket.get('is_resolved'):
            resolved_badge = '<span class="ml-2 text-xs text-green-600">âœ“ Resolved</span>'
        
        html += f"""
        <div class="ticket-card bg-white border border-gray-200 rounded-lg p-3 hover:border-indigo-300 transition">
            <div class="flex items-center justify-between mb-1">
                <span class="font-semibold text-gray-800">Ticket #{ticket['id']}</span>
                <div class="flex items-center gap-2">
                    <span class="inline-block px-2 py-0.5 text-xs font-medium rounded {status_class}">
                        {status.upper().replace('_', ' ')}
                    </span>
                    {resolved_badge}
                </div>
            </div>
            <p class="text-sm text-gray-600 mb-1">{query_preview}</p>
            <div class="flex justify-between items-center text-xs text-gray-400">
                <span>Created: {ticket.get('created_at', 'N/A')}</span>
            </div>
        </div>
        """
    
    html += """
        </div>
    </div>
    """
    
    return html


def format_success_message(message_text: str) -> str:
    """Format success messages nicely"""
    return f"""
    <div class="bg-green-50 border border-green-200 rounded-lg p-4 my-2">
        <div class="flex items-start">
            <svg class="w-5 h-5 text-green-600 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div>
                <p class="text-sm text-green-800">{message_text}</p>
            </div>
        </div>
    </div>
    """


def format_error_message(error_text: str) -> str:
    """Format error messages nicely"""
    return f"""
    <div class="bg-red-50 border border-red-200 rounded-lg p-4 my-2">
        <div class="flex items-start">
            <svg class="w-5 h-5 text-red-600 mt-0.5 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <div>
                <h4 class="text-sm font-medium text-red-800">Error</h4>
                <p class="text-sm text-red-700 mt-1">{error_text}</p>
            </div>
        </div>
    </div>
    """

# ============ FRONTEND ROUTES ============

@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Landing page"""
    return templates.TemplateResponse("landing.html", {"request": request})

@app.get("/auth/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page"""
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/auth/login", response_class=HTMLResponse)
async def login_page(request: Request, success: str = None):
    """Login page"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "success_message": success
    })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

# ============================================================================
# HTMX CHAT ENDPOINTS WITH LLM INTEGRATION
# ============================================================================

@app.post("/htmx/chat/init")
async def chat_init(request: Request):
    """Initialize chat with welcome message and create new session"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return HTMLResponse("<div class='text-red-500'>Unauthorized</div>", status_code=401)
    
    token = auth_header.replace("Bearer ", "")
    user = get_user_from_token(token)
    
    if not user:
        return HTMLResponse("<div class='text-red-500'>Unauthorized</div>", status_code=401)
    
    # Create new chat session for this user
    session_id = f"user_{user['id']}"
    
    # Initialize with system message
    system_prompt = f"""You are a helpful support assistant for HelpHub ticket management system.

Current user information:
- Username: {user['username']}
- User ID: {user['id']}
- Role: {user.get('role', 'user')}

You can help users with their support tickets:
- View all their tickets or filter by status (open, in_progress, resolved, closed)
- Get detailed information about specific tickets
- Create new support tickets
- Update ticket information (admins have more permissions)

When users ask about tickets:
- Use the get_ticket tool for specific ticket IDs
- Use the get_tickets tool to list multiple tickets with filters
- Use create_ticket to create new tickets
- Use update_ticket to modify ticket information

Important guidelines:
- Be conversational and friendly
- Format responses clearly using the HTML tools provide
- If a user mentions a ticket number, fetch its details
- If they ask about status, filter tickets accordingly
- Always acknowledge what you've done and offer to help further

Remember: Regular users can only see their own tickets. Admins can see all tickets."""

    chat_sessions[session_id] = [SystemMessage(content=system_prompt)]
    
    # Get initial ticket count
    try:
        with get_db() as db:
            result = db.execute(text("""
                SELECT COUNT(*) FROM tickets 
                WHERE user_id = :user_id
            """), {"user_id": user["id"]})
            ticket_count = result.fetchone()[0]
            
            welcome_msg = f"""Hello {user['username']}! ðŸ‘‹

I'm your AI support assistant. I can help you with your support tickets.

You have **{ticket_count} ticket{'s' if ticket_count != 1 else ''}** in the system.

What would you like to do?
- View your tickets (try: "show my open tickets")
- Get details on a specific ticket (try: "show ticket #123")
- Create a new ticket (try: "I need help with...")
- Check ticket status (try: "what tickets need attention?")

Just ask me anything! ðŸš€"""
            
            return templates.TemplateResponse("partials/chat_message.html", {
                "request": request,
                "message": welcome_msg,
                "is_system": True
            })
    except Exception as e:
        logger.error(f"Error in chat init: {e}")
        return HTMLResponse("<div class='text-red-500'>Error loading chat</div>")


@app.post("/htmx/chat/send")
async def chat_send(request: Request, message: str = Form(...)):
    """Handle chat messages using LLM with tools"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return HTMLResponse("<div class='text-red-500'>Unauthorized</div>", status_code=401)
    
    token = auth_header.replace("Bearer ", "")
    user = get_user_from_token(token)
    
    if not user:
        return HTMLResponse("<div class='text-red-500'>Unauthorized</div>", status_code=401)
    
    message = message.strip()
    session_id = f"user_{user['id']}"
    
    # Initialize session if doesn't exist
#     if session_id not in chat_sessions:
#         system_prompt = f"""You are a helpful support assistant for HelpHub.
# Current user: {user['username']} (ID: {user['id']}, Role: {user.get('role', 'user')})"""
#         chat_sessions[session_id] = [SystemMessage(content=system_prompt)]
    if session_id not in chat_sessions:
        return HTMLResponse(
        "<div class='text-red-500'>Session not initialized. Refresh the page.</div>",
        status_code=400
        )

    try:
        # Get current chat history
        chat_history = chat_sessions[session_id]
        
        # Add user message
        msgs = chat_history + [HumanMessage(content=message)]
        
        # Call your LLM with tools (from mcp_cliento.py)
        # Pass user context
        updated_history = await tool_llm(
            msgs
        )
        
        # Update session
        chat_sessions[session_id] = updated_history
        
        # Get the last AI message
        last_message = updated_history[-1]
        
        if isinstance(last_message, AIMessage):
            response_text = last_message.content
            
            # Check if response contains HTML
            is_html = any(tag in response_text for tag in ['<div', '<span', '<ul', '<li', '<p class'])
            
            return templates.TemplateResponse("partials/chat_message.html", {
                "request": request,
                "message": response_text,
                "is_system": True,
                "is_html": is_html
            })
        else:
            return templates.TemplateResponse("partials/chat_message.html", {
                "request": request,
                "message": "I encountered an issue processing your request. Please try again.",
                "is_system": True
            })
            
    except Exception as e:
        logger.error(f"Error in chat send: {e}", exc_info=True)
        error_html = format_error_message(f"An error occurred while processing your message: {str(e)}")
        return templates.TemplateResponse("partials/chat_message.html", {
            "request": request,
            "message": error_html,
            "is_system": True,
            "is_html": True
        })


@app.post("/htmx/chat/clear")
async def chat_clear(request: Request):
    """Clear chat session"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return HTMLResponse("<div class='text-red-500'>Unauthorized</div>", status_code=401)
    
    token = auth_header.replace("Bearer ", "")
    user = get_user_from_token(token)
    
    if not user:
        return HTMLResponse("<div class='text-red-500'>Unauthorized</div>", status_code=401)
    
    session_id = f"user_{user['id']}"
    
    # Remove session
    if session_id in chat_sessions:
        del chat_sessions[session_id]
    
    return HTMLResponse(format_success_message("Chat cleared successfully! Starting fresh conversation."))

# ============ API ROUTES (Original) ============

@app.post("/api/auth/register", response_model=User)
async def register(user: UserCreate):
    try:
        with get_db() as db:
            result = db.execute(
                text("SELECT username FROM users WHERE username = :username OR email = :email"),
                {"username": user.username, "email": user.email}
            )
            
            if result.fetchone():
                raise HTTPException(
                    status_code=400,
                    detail="Username or email already registered"
                )
            
            role = "user" if user.role != "admin" else "user"
            
            hashed_password = get_password_hash(user.password)
            db.execute(text("""
                INSERT INTO users (username, email, full_name, hashed_password, role)
                VALUES (:username, :email, :full_name, :hashed_password, :role)
            """), {
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "hashed_password": hashed_password,
                "role": role
            })
            db.commit()

            return User(
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                is_active=True,
                role=role
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during user registration")

@app.post("/api/auth/login", response_model=Token)
async def login(user: UserLogin):
    authenticated_user = authenticate_user(user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": authenticated_user["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me", response_model=User)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return User(
        username=current_user["username"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        is_active=current_user.get("is_active", True),
        role=current_user.get("role", "user")
    )

@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(ticket: TicketCreate, current_user: dict = Depends(get_current_user)):
    try:
        with get_db() as db:
            db.execute(text("""
                INSERT INTO tickets (user_id, query, status, responded_by)
                VALUES (:user_id, :query, :status, :responded_by)
            """), {
                "user_id": current_user["id"],
                "query": ticket.query,
                "status": TicketStatus.OPEN.value,
                "responded_by": RespondedBy.NONE.value
            })
            db.commit()
            
            result = db.execute(text("""
                SELECT 
                    t.id, t.user_id, u.username, 
                    t.query, t.status, t.llm_response, t.final_response, 
                    t.responded_by, t.is_resolved, t.user_satisfied, 
                    t.created_at, t.updated_at
                FROM tickets t
                JOIN users u ON t.user_id = u.id
                WHERE t.user_id = :user_id
                ORDER BY t.created_at DESC
                LIMIT 1
            """), {"user_id": current_user["id"]})

            row = result.mappings().fetchone()
            return TicketResponse(
                id=row["id"],
                user_id=row["user_id"],
                username=row["username"],
                query=row["query"],
                status=row["status"],
                llm_response=row["llm_response"],
                final_response=row["final_response"],
                responded_by=row["responded_by"],
                is_resolved=row["is_resolved"],
                user_satisfied=row["user_satisfied"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        raise HTTPException(status_code=500, detail="Error creating ticket")

@app.get("/api/tickets", response_model=List[TicketResponse])
async def get_tickets(
    current_user: dict = Depends(get_current_user),
    user_id: Optional[int] = Query(None),
    status: Optional[TicketStatus] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    responded_by: Optional[RespondedBy] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    try:
        with get_db() as db:
            query = """
                SELECT 
                    t.id, t.user_id, u.username, 
                    t.query, t.status, t.llm_response, t.final_response, 
                    t.responded_by, t.is_resolved, t.user_satisfied, 
                    t.created_at, t.updated_at
                FROM tickets t
                JOIN users u ON t.user_id = u.id
                WHERE 1=1
            """
            params = {}
            
            if current_user["role"] != "admin":
                query += " AND t.user_id = :current_user_id"
                params["current_user_id"] = current_user["id"]
            
            if user_id is not None:
                query += " AND t.user_id = :user_id"
                params["user_id"] = user_id
            
            if status is not None:
                query += " AND t.status = :status"
                params["status"] = status.value
            
            if is_resolved is not None:
                query += " AND t.is_resolved = :is_resolved"
                params["is_resolved"] = is_resolved
            
            if responded_by is not None:
                query += " AND t.responded_by = :responded_by"
                params["responded_by"] = responded_by.value
            
            query += " ORDER BY t.created_at DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset
            
            result = db.execute(text(query), params)
            tickets = result.mappings().fetchall()
            
            return [
                TicketResponse(
                    id=row["id"],
                    user_id=row["user_id"],
                    username=row["username"],
                    query=row["query"],
                    status=row["status"],
                    llm_response=row["llm_response"],
                    final_response=row["final_response"],
                    responded_by=row["responded_by"],
                    is_resolved=row["is_resolved"],
                    user_satisfied=row["user_satisfied"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in tickets
            ]
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        raise HTTPException(status_code=500, detail="Error fetching tickets")

@app.get("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: int, current_user: dict = Depends(get_current_user)):
    try:
        with get_db() as db:
            result = db.execute(text("""
                SELECT 
                    t.id, t.user_id, u.username, 
                    t.query, t.status, t.llm_response, t.final_response, 
                    t.responded_by, t.is_resolved, t.user_satisfied, 
                    t.created_at, t.updated_at
                FROM tickets t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = :ticket_id
            """), {"ticket_id": ticket_id})
            
            row = result.mappings().fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="Ticket not found")
            
            if current_user["role"] != "admin" and row["user_id"] != current_user["id"]:
                raise HTTPException(status_code=403, detail="Not authorized to view this ticket")
            
            return TicketResponse(
                id=row["id"],
                user_id=row["user_id"],
                username=row["username"],
                query=row["query"],
                status=row["status"],
                llm_response=row["llm_response"],
                final_response=row["final_response"],
                responded_by=row["responded_by"],
                is_resolved=row["is_resolved"],
                user_satisfied=row["user_satisfied"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
    except Exception as e:
        logger.error(f"Error fetching ticket: {e}")
        raise HTTPException(status_code=500, detail="Error fetching ticket")

@app.patch("/api/tickets/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    current_user: dict = Depends(get_current_user)
):
    try:
        with get_db() as db:
            result = db.execute(text("SELECT user_id FROM tickets WHERE id = :ticket_id"), {"ticket_id": ticket_id})
            ticket = result.fetchone()
            
            if not ticket:
                raise HTTPException(status_code=404, detail="Ticket not found")
            
            update_fields = []
            params = {"ticket_id": ticket_id}
            
            if current_user["role"] != "admin":
                if ticket[0] != current_user["id"]:
                    raise HTTPException(status_code=403, detail="Not authorized to update this ticket")
                
                if ticket_update.user_satisfied is not None:
                    update_fields.append("user_satisfied = :user_satisfied")
                    params["user_satisfied"] = ticket_update.user_satisfied
            else:
                # Admins can update all fields
                if ticket_update.status is not None:
                    update_fields.append("status = :status")
                    params["status"] = ticket_update.status.value
                
                if ticket_update.llm_response is not None:
                    update_fields.append("llm_response = :llm_response")
                    params["llm_response"] = ticket_update.llm_response
                
                if ticket_update.final_response is not None:
                    update_fields.append("final_response = :final_response")
                    params["final_response"] = ticket_update.final_response
                
                if ticket_update.responded_by is not None:
                    update_fields.append("responded_by = :responded_by")
                    params["responded_by"] = ticket_update.responded_by.value
                
                if ticket_update.is_resolved is not None:
                    update_fields.append("is_resolved = :is_resolved")
                    params["is_resolved"] = ticket_update.is_resolved
                
                if ticket_update.user_satisfied is not None:
                    update_fields.append("user_satisfied = :user_satisfied")
                    params["user_satisfied"] = ticket_update.user_satisfied
            
            if not update_fields:
                raise HTTPException(status_code=400, detail="No fields to update")

            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            update_query = f"UPDATE tickets SET {', '.join(update_fields)} WHERE id = :ticket_id"
            db.execute(text(update_query), params)
            db.commit()
            
            result = db.execute(text("""
                SELECT 
                    t.id, t.user_id, u.username, 
                    t.query, t.status, t.llm_response, t.final_response, 
                    t.responded_by, t.is_resolved, t.user_satisfied, 
                    t.created_at, t.updated_at
                FROM tickets t
                JOIN users u ON t.user_id = u.id
                WHERE t.id = :ticket_id
            """), {"ticket_id": ticket_id})
            
            row = result.mappings().fetchone()
            
            return TicketResponse(
                id=row["id"],
                user_id=row["user_id"],
                username=row["username"],
                query=row["query"],
                status=row["status"],
                llm_response=row["llm_response"],
                final_response=row["final_response"],
                responded_by=row["responded_by"],
                is_resolved=row["is_resolved"],
                user_satisfied=row["user_satisfied"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")
        raise HTTPException(status_code=500, detail="Error updating ticket")

@app.get("/api/admin/stats")
async def get_admin_stats(current_admin: dict = Depends(get_current_admin)):
    try:
        with get_db() as db:
            stats = {}
            
            result = db.execute(text("SELECT COUNT(*) FROM tickets"))
            stats["total_tickets"] = result.fetchone()[0]
            
            result = db.execute(text("""
                SELECT status, COUNT(*) as count 
                FROM tickets 
                GROUP BY status
            """))
            stats["tickets_by_status"] = {row[0]: row[1] for row in result.fetchall()}
            
            result = db.execute(text("SELECT COUNT(*) FROM tickets WHERE is_resolved = 1"))
            stats["resolved_tickets"] = result.fetchone()[0]
            
            result = db.execute(text("""
                SELECT 
                    COUNT(CASE WHEN user_satisfied = 1 THEN 1 END) as satisfied,
                    COUNT(CASE WHEN user_satisfied = 0 THEN 1 END) as unsatisfied,
                    COUNT(CASE WHEN user_satisfied IS NULL THEN 1 END) as no_response
                FROM tickets
            """))
            satisfaction = result.fetchone()
            stats["user_satisfaction"] = {
                "satisfied": satisfaction[0],
                "unsatisfied": satisfaction[1],
                "no_response": satisfaction[2]
            }
            
            result = db.execute(text("""
                SELECT responded_by, COUNT(*) as count 
                FROM tickets 
                GROUP BY responded_by
            """))
            stats["response_types"] = {row[0]: row[1] for row in result.fetchall()}
            
            result = db.execute(text("SELECT COUNT(*) FROM users"))
            stats["total_users"] = result.fetchone()[0]
            
            return stats
    except Exception as e:
        logger.error(f"Error fetching admin stats: {e}")
        raise HTTPException(status_code=500, detail="Error fetching statistics")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
    
# uvicorn main:app --reload --host 0.0.0.0 --port 8000