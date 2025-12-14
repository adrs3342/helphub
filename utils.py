from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
from contextlib import contextmanager, asynccontextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging
load_dotenv()
from passlib.context import CryptContext
from security import *


# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Database Configuration - SQLite3
database_name = "ticketing_tool.db"
DATABASE_URL = f"sqlite:///{database_name}"

# SQLAlchemy setup for SQLite
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)




class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_LLM = "pending_llm"
    PENDING_HUMAN = "pending_human"
    RESOLVED = "resolved"
    CLOSED = "closed"

class RespondedBy(str, Enum):
    LLM = "llm"
    HUMAN = "human"
    NONE = "none"

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"

# Authentication models
class User(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    role: str = UserRole.USER

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    full_name: Optional[str] = None
    role: Optional[str] = UserRole.USER

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Ticket models
class TicketCreate(BaseModel):
    query: str = Field(..., min_length=10, description="User query/issue description")

class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = None
    llm_response: Optional[str] = None
    final_response: Optional[str] = None
    responded_by: Optional[RespondedBy] = None
    is_resolved: Optional[bool] = None
    user_satisfied: Optional[bool] = None

class TicketResponse(BaseModel):
    id: int
    user_id: int
    username: str
    query: str
    status: str
    llm_response: Optional[str]
    final_response: Optional[str]
    responded_by: Optional[str]
    is_resolved: bool
    user_satisfied: Optional[bool]
    created_at: str
    updated_at: str

# Database connection context manager
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



def initialize_database_and_tables():
    """Creates necessary tables for SQLite database."""
    try:
        with engine.connect() as conn:
            # Create users table with role
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    full_name VARCHAR(100),
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))

            # Create tickets table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    status VARCHAR(20) DEFAULT 'open',
                    llm_response TEXT,
                    final_response TEXT,
                    responded_by VARCHAR(20) DEFAULT 'none',
                    is_resolved BOOLEAN DEFAULT FALSE,
                    user_satisfied BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """))
            
            conn.commit()
            logger.info("SQLite database and tables initialized successfully.")
            
            # Create default admin if not exists
            result = conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'"))
            admin_count = result.fetchone()[0]
            
            if admin_count == 0:
                admin_password = pwd_context.hash("admin123")
                conn.execute(text("""
                    INSERT INTO users (username, email, full_name, hashed_password, role)
                    VALUES ('admin', 'admin@system.com', 'System Admin', :password, 'admin')
                """), {"password": admin_password})
                conn.commit()
                logger.info("Default admin user created (username: admin, password: admin123)")
                
    except Exception as e:
        logger.error(f"Error initializing database tables: {e}")
        raise