"""
FastAPI Integration Example for NexaMem

This example demonstrates how to integrate NexaMem into a FastAPI application
for high-performance conversational memory management.
"""

import os
import time
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from nexamem import create_conversation_memory, ConversationMemoryAdapter


# Pydantic models for request/response
class ConversationTurn(BaseModel):
    """Request model for adding a conversation turn."""
    content: str = Field(..., description="The conversation content")
    user_id: Optional[str] = Field(None, description="User identifier")
    turn_type: str = Field("user", description="Type of turn: user or assistant")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class ConversationTurnResponse(BaseModel):
    """Response model for conversation turn operations."""
    success: bool
    turn_id: str
    conversation_id: str
    timestamp: float


class ConversationHistory(BaseModel):
    """Response model for conversation history."""
    success: bool
    conversation_id: str
    history: List[Dict[str, Any]]
    count: int


class SearchResults(BaseModel):
    """Response model for search operations."""
    success: bool
    query: str
    results: List[Dict[str, Any]]
    count: int


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    service: str
    timestamp: float
    memory_service_status: str


class ConversationSummary(BaseModel):
    """Request model for conversation summary."""
    summary: str = Field(..., description="The conversation summary")


# Global memory service (in production, use dependency injection)
memory_service: Optional[ConversationMemoryAdapter] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    global memory_service
    
    # Startup: Initialize memory service
    print("🚀 Starting FastAPI NexaMem Integration")
    
    try:
        memory_service = create_conversation_memory(
            service_type=os.getenv("NEXAMEM_SERVICE_TYPE", "memory"),
            config={
                "default_scope": "fastapi_chat_app",
                "redis_hostname": os.getenv("AZURE_REDIS_HOSTNAME"),
                "redis_access_key": os.getenv("AZURE_REDIS_ACCESS_KEY"),
                "redis_port": int(os.getenv("AZURE_REDIS_PORT", "6380")),
                "redis_ssl": os.getenv("AZURE_REDIS_SSL", "true").lower() == "true"
            },
            async_preferred=True
        )
        print("✅ Memory service initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize memory service: {e}")
        raise
    
    yield
    
    # Shutdown
    print("🛑 Shutting down FastAPI NexaMem Integration")


# Create FastAPI app with lifespan management
app = FastAPI(
    title="NexaMem FastAPI Integration",
    description="High-performance conversational memory API using NexaMem",
    version="1.0.0",
    lifespan=lifespan
)


# Dependency to get memory service
async def get_memory_service() -> ConversationMemoryAdapter:
    """Dependency to inject memory service."""
    if memory_service is None:
        raise HTTPException(status_code=500, detail="Memory service not initialized")
    return memory_service


@app.get("/health", response_model=HealthResponse)
async def health_check(memory: ConversationMemoryAdapter = Depends(get_memory_service)):
    """Health check endpoint with memory service verification."""
    try:
        # Test memory service by storing and retrieving a test turn
        test_turn_id = await memory.store_turn(
            conversation_id="health_check",
            content="Health check test",
            metadata={"type": "health_check", "timestamp": time.time()}
        )
        
        # Clean up test data
        # Note: In a real implementation, you might skip cleanup or use a dedicated health check method
        
        return HealthResponse(
            status="healthy",
            service="fastapi-nexamem-integration",
            timestamp=time.time(),
            memory_service_status="operational"
        )
        
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            service="fastapi-nexamem-integration", 
            timestamp=time.time(),
            memory_service_status=f"error: {str(e)}"
        )


@app.post("/conversation/{conversation_id}/turn", response_model=ConversationTurnResponse)
async def add_conversation_turn(
    conversation_id: str,
    turn: ConversationTurn,
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    """Add a new turn to a conversation."""
    try:
        # Prepare metadata
        metadata = {
            "user_id": turn.user_id,
            "turn_type": turn.turn_type,
            "timestamp": time.time(),
            "source": "fastapi_app",
            **(turn.metadata or {})
        }
        
        # Store the conversation turn
        turn_id = await memory.store_turn(
            conversation_id=conversation_id,
            content=turn.content,
            metadata=metadata
        )
        
        return ConversationTurnResponse(
            success=True,
            turn_id=turn_id,
            conversation_id=conversation_id,
            timestamp=metadata["timestamp"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to store conversation turn: {str(e)}"
        )


@app.get("/conversation/{conversation_id}/history", response_model=ConversationHistory)
async def get_conversation_history(
    conversation_id: str,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of turns to retrieve"),
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    """Get conversation history."""
    try:
        # Get conversation history
        history = await memory.get_history(
            conversation_id=conversation_id,
            limit=limit
        )
        
        return ConversationHistory(
            success=True,
            conversation_id=conversation_id,
            history=history,
            count=len(history)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@app.get("/conversations/search", response_model=SearchResults)
async def search_conversations(
    q: str = Query(..., description="Search query string"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    """Search across all conversations."""
    try:
        # Search conversations
        results = await memory.search_conversations(
            query=q,
            limit=limit
        )
        
        return SearchResults(
            success=True,
            query=q,
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search conversations: {str(e)}"
        )


@app.post("/conversation/{conversation_id}/summary", response_model=ConversationTurnResponse)
async def create_conversation_summary(
    conversation_id: str,
    summary: ConversationSummary,
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    """Create a summary of a conversation."""
    try:
        # Store summary as a special turn
        summary_id = await memory.store_turn(
            conversation_id=conversation_id,
            content=summary.summary,
            metadata={
                "type": "summary",
                "timestamp": time.time(),
                "created_by": "system",
                "source": "fastapi_app"
            }
        )
        
        return ConversationTurnResponse(
            success=True,
            turn_id=summary_id,
            conversation_id=conversation_id,
            timestamp=time.time()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create conversation summary: {str(e)}"
        )


@app.get("/conversation/{conversation_id}/analytics")
async def get_conversation_analytics(
    conversation_id: str,
    memory: ConversationMemoryAdapter = Depends(get_memory_service)
):
    """Get analytics for a conversation (demonstration of custom endpoints)."""
    try:
        # Get conversation history
        history = await memory.get_history(
            conversation_id=conversation_id,
            limit=1000  # Get all turns for analytics
        )
        
        # Basic analytics
        total_turns = len(history)
        user_turns = sum(1 for turn in history if turn.get("metadata", {}).get("turn_type") == "user")
        assistant_turns = sum(1 for turn in history if turn.get("metadata", {}).get("turn_type") == "assistant")
        
        # Word count analysis
        total_words = sum(len(turn["content"].split()) for turn in history)
        avg_words_per_turn = total_words / total_turns if total_turns > 0 else 0
        
        # Time analysis
        timestamps = [turn.get("timestamp", 0) for turn in history if turn.get("timestamp")]
        conversation_duration = max(timestamps) - min(timestamps) if len(timestamps) > 1 else 0
        
        return {
            "success": True,
            "conversation_id": conversation_id,
            "analytics": {
                "total_turns": total_turns,
                "user_turns": user_turns,
                "assistant_turns": assistant_turns,
                "total_words": total_words,
                "avg_words_per_turn": round(avg_words_per_turn, 2),
                "conversation_duration_seconds": round(conversation_duration, 2)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get conversation analytics: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "FastAPI NexaMem Integration",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "add_turn": "POST /conversation/{id}/turn",
            "get_history": "GET /conversation/{id}/history",
            "search": "GET /conversations/search",
            "create_summary": "POST /conversation/{id}/summary",
            "analytics": "GET /conversation/{id}/analytics"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    print("Starting FastAPI NexaMem Integration")
    print("Available endpoints:")
    print("  POST /conversation/{id}/turn - Add conversation turn")
    print("  GET  /conversation/{id}/history - Get conversation history")
    print("  GET  /conversations/search - Search conversations")
    print("  POST /conversation/{id}/summary - Create conversation summary")
    print("  GET  /conversation/{id}/analytics - Get conversation analytics")
    print("  GET  /health - Health check")
    print("  GET  /docs - Interactive API documentation")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("FASTAPI_RELOAD", "true").lower() == "true",
        log_level="info"
    )