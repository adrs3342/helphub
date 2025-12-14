import asyncio
from fastapi import FastAPI
from fastmcp import FastMCP
from utils import *
from typing import Optional
mcp = FastMCP("helphub")
from fastapi import HTTPException

def raise_error(message: str, status_code: int = 400):
    raise HTTPException(
        status_code=status_code,
        detail={"error": message}
    )

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
        
        # Add resolution indicator
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
                {f"<span>By: {ticket.get('username', 'Unknown')}</span>" if ticket.get('username') else ""}
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


def ticket_response_to_dict(ticket: TicketResponse) -> dict:
    """Convert TicketResponse object to dictionary for formatting"""
    return {
        'id': ticket.id,
        'user_id': ticket.user_id,
        'username': ticket.username,
        'query': ticket.query,
        'status': ticket.status,
        'llm_response': ticket.llm_response,
        'final_response': ticket.final_response,
        'responded_by': ticket.responded_by,
        'is_resolved': ticket.is_resolved,
        'user_satisfied': ticket.user_satisfied,
        'created_at': str(ticket.created_at) if ticket.created_at else 'N/A',
        'updated_at': str(ticket.updated_at) if ticket.updated_at else 'N/A'
    }


# ============================================================================
# MCP TOOLS WITH FORMATTED RESPONSES
# ============================================================================

@mcp.tool()
async def create_ticket(ticket: TicketCreate, user_id: int) -> str:
    """
    Create a new support ticket.

    Args:
        ticket: The ticket information containing the query.
        user_id: ID of the user creating the ticket.
    
    Returns:
        Formatted HTML showing the created ticket details.
    """
    try:
        with get_db() as db:
            db.execute(text("""
                INSERT INTO tickets (user_id, query, status, responded_by)
                VALUES (:user_id, :query, :status, :responded_by)
            """), {
                "user_id": user_id,
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
            """), {"user_id": user_id})

            row = result.mappings().fetchone()
            ticket_data = ticket_response_to_dict(TicketResponse(
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
            ))
            
            success_msg = format_success_message(f"âœ… Ticket #{ticket_data['id']} created successfully!")
            ticket_html = format_ticket_details(ticket_data)
            
            return success_msg + ticket_html
            
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        return format_error_message(f"Failed to create ticket: {str(e)}")


@mcp.tool()
async def get_tickets(
    current_user_id: int,
    current_user_role: str,
    user_id: Optional[int] = None,
    status: Optional[TicketStatus] = None,
    is_resolved: Optional[bool] = None,
    responded_by: Optional[RespondedBy] = None,
    limit: int = 100,
    offset: int = 0
) -> str:
    """
    Retrieve support tickets with optional filtering.
    
    Access control: Admins see all tickets; regular users see only their own.
    
    Args:
        current_user_id: ID of the user making the request
        current_user_role: User role ("admin" views all, others view own tickets only)
        user_id: Filter by specific user (admin-only)
        status: Filter by status (open, in_progress, resolved, closed)
        is_resolved: Filter by resolution status
        responded_by: Filter by responder (llm, human, none)
        limit: Max results to return (default: 100)
        offset: Results to skip for pagination (default: 0)
    
    Returns:
        Formatted HTML showing list of tickets matching the criteria.
    """
    try:
        with get_db() as db:
            query = """
                SELECT
                    t.id, t.user_id, u.username, t.query, t.status, t.llm_response,
                    t.final_response, t.responded_by, t.is_resolved, t.user_satisfied,
                    t.created_at, t.updated_at
                FROM tickets t
                JOIN users u ON t.user_id = u.id
                WHERE 1 = 1
            """
            params = {}

            # Role-based access control
            if current_user_role != "admin":
                query += " AND t.user_id = :current_user_id"
                params["current_user_id"] = current_user_id
            
            # Apply filters
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
            rows = result.mappings().fetchall()

            tickets = [
                {
                    'id': row["id"],
                    'user_id': row["user_id"],
                    'username': row["username"],
                    'query': row["query"],
                    'status': row["status"],
                    'llm_response': row["llm_response"],
                    'final_response': row["final_response"],
                    'responded_by': row["responded_by"],
                    'is_resolved': row["is_resolved"],
                    'user_satisfied': row["user_satisfied"],
                    'created_at': str(row["created_at"]) if row["created_at"] else 'N/A',
                    'updated_at': str(row["updated_at"]) if row["updated_at"] else 'N/A'
                }
                for row in rows
            ]
            
            # Create descriptive title based on filters
            title_parts = []
            if status:
                title_parts.append(f"{status.value.upper()}")
            if is_resolved is not None:
                title_parts.append("RESOLVED" if is_resolved else "UNRESOLVED")
            if responded_by:
                title_parts.append(f"by {responded_by.value.upper()}")
            
            title = " ".join(title_parts) + " Tickets" if title_parts else "Your Tickets"
            
            return format_ticket_list(tickets, title)
            
    except Exception as e:
        logger.error(f"Error fetching tickets: {e}")
        return format_error_message(f"Failed to fetch tickets: {str(e)}")


@mcp.tool()
async def get_ticket(ticket_id: int, current_user_id: int, current_user_role: str) -> str:
    """
    Retrieve a single ticket by its ID.
    
    Access control: Admins can view any ticket; regular users can only view their own.
    
    Args:
        ticket_id: The ID of the ticket to retrieve
        current_user_id: ID of the user making the request
        current_user_role: User role ("admin" can view any ticket, others only their own)
    
    Returns:
        Formatted HTML showing detailed ticket information.
    """
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
                return format_error_message(f"Ticket #{ticket_id} not found.")
            
            # Check authorization
            if current_user_role != "admin" and row["user_id"] != current_user_id:
                return format_error_message("You don't have permission to view this ticket.")
            
            ticket_data = {
                'id': row["id"],
                'user_id': row["user_id"],
                'username': row["username"],
                'query': row["query"],
                'status': row["status"],
                'llm_response': row["llm_response"],
                'final_response': row["final_response"],
                'responded_by': row["responded_by"],
                'is_resolved': row["is_resolved"],
                'user_satisfied': row["user_satisfied"],
                'created_at': str(row["created_at"]) if row["created_at"] else 'N/A',
                'updated_at': str(row["updated_at"]) if row["updated_at"] else 'N/A'
            }
            
            return format_ticket_details(ticket_data)
            
    except Exception as e:
        logger.error(f"Error fetching ticket: {e}")
        return format_error_message(f"Failed to fetch ticket: {str(e)}")


@mcp.tool()
async def update_ticket(
    ticket_id: int,
    ticket_update: TicketUpdate,
    current_user_id: int,
    current_user_role: str
) -> str:
    """
    Update an existing ticket with role-based field restrictions.
    
    Access control:
    - Regular users: Can only update their own tickets and only the 'user_satisfied' field
    - Admins: Can update any ticket and all fields
    
    Args:
        ticket_id: ID of the ticket to update
        ticket_update: Fields to update (status, responses, satisfaction, etc.)
        current_user_id: ID of the user making the request
        current_user_role: User role determining update permissions
    
    Returns:
        Formatted HTML showing the updated ticket details.
    """
    try:
        with get_db() as db:
            result = db.execute(text("SELECT user_id FROM tickets WHERE id = :ticket_id"), {"ticket_id": ticket_id})
            ticket = result.fetchone()
            
            if not ticket:
                return format_error_message(f"Ticket #{ticket_id} not found.")
            
            update_fields = []
            params = {"ticket_id": ticket_id}
            
            # Regular users can only update their own tickets and only satisfaction
            if current_user_role != "admin":
                if ticket[0] != current_user_id:
                    return format_error_message("You don't have permission to update this ticket.")
                
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
                return format_error_message("No fields provided to update.")
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            
            update_query = f"UPDATE tickets SET {', '.join(update_fields)} WHERE id = :ticket_id"
            db.execute(text(update_query), params)
            db.commit()
            
            # Fetch updated ticket
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
            
            ticket_data = {
                'id': row["id"],
                'user_id': row["user_id"],
                'username': row["username"],
                'query': row["query"],
                'status': row["status"],
                'llm_response': row["llm_response"],
                'final_response': row["final_response"],
                'responded_by': row["responded_by"],
                'is_resolved': row["is_resolved"],
                'user_satisfied': row["user_satisfied"],
                'created_at': str(row["created_at"]) if row["created_at"] else 'N/A',
                'updated_at': str(row["updated_at"]) if row["updated_at"] else 'N/A'
            }
            
            success_msg = format_success_message(f"âœ… Ticket #{ticket_id} updated successfully!")
            ticket_html = format_ticket_details(ticket_data)
            
            return success_msg + ticket_html
            
    except HTTPException as he:
        return format_error_message(str(he.detail))
    except Exception as e:
        logger.error(f"Error updating ticket: {e}")
        return format_error_message(f"Failed to update ticket: {str(e)}")