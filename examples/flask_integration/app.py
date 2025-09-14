"""
Flask Integration Example for NexaMem

This example demonstrates how to integrate NexaMem into a Flask application
for conversational memory management.
"""

import os
import time
import asyncio
from typing import Dict, Any

from flask import Flask, request, jsonify
from nexamem import create_conversation_memory


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Initialize memory service (in production, this would be in app factory or DI container)
    app.memory_service = create_conversation_memory(
        service_type=os.getenv("NEXAMEM_SERVICE_TYPE", "memory"),  # Use memory for demo
        config={
            "default_scope": "flask_chat_app",
            "redis_hostname": os.getenv("AZURE_REDIS_HOSTNAME"),
            "redis_access_key": os.getenv("AZURE_REDIS_ACCESS_KEY"),
            "redis_port": int(os.getenv("AZURE_REDIS_PORT", "6380")),
            "redis_ssl": os.getenv("AZURE_REDIS_SSL", "true").lower() == "true"
        },
        async_preferred=True
    )
    
    return app


app = create_app()


@app.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "flask-nexamem-integration",
        "timestamp": time.time()
    })


@app.route("/conversation/<conversation_id>/turn", methods=["POST"])
def add_conversation_turn(conversation_id: str):
    """Add a new turn to a conversation.
    
    Expected JSON:
    {
        "content": "User message content",
        "user_id": "user123",
        "turn_type": "user|assistant",
        "metadata": {...}
    }
    """
    try:
        data = request.get_json()
        if not data or "content" not in data:
            return jsonify({"error": "Missing 'content' in request body"}), 400
        
        # Prepare metadata
        metadata = {
            "user_id": data.get("user_id"),
            "turn_type": data.get("turn_type", "user"),
            "timestamp": time.time(),
            "source": "flask_app",
            **(data.get("metadata", {}))
        }
        
        # Store the conversation turn
        turn_id = asyncio.run(app.memory_service.store_turn(
            conversation_id=conversation_id,
            content=data["content"],
            metadata=metadata
        ))
        
        return jsonify({
            "success": True,
            "turn_id": turn_id,
            "conversation_id": conversation_id,
            "timestamp": metadata["timestamp"]
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to store conversation turn: {str(e)}"
        }), 500


@app.route("/conversation/<conversation_id>/history")
def get_conversation_history(conversation_id: str):
    """Get conversation history.
    
    Query parameters:
    - limit: Maximum number of turns to retrieve (default: 10)
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        
        # Get conversation history
        history = asyncio.run(app.memory_service.get_history(
            conversation_id=conversation_id,
            limit=limit
        ))
        
        return jsonify({
            "success": True,
            "conversation_id": conversation_id,
            "history": history,
            "count": len(history)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to retrieve conversation history: {str(e)}"
        }), 500


@app.route("/conversations/search")
def search_conversations():
    """Search across all conversations.
    
    Query parameters:
    - q: Search query string
    - limit: Maximum number of results (default: 10)
    """
    try:
        query = request.args.get("q")
        if not query:
            return jsonify({"error": "Missing 'q' query parameter"}), 400
        
        limit = request.args.get("limit", 10, type=int)
        
        # Search conversations
        results = asyncio.run(app.memory_service.search_conversations(
            query=query,
            limit=limit
        ))
        
        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to search conversations: {str(e)}"
        }), 500


@app.route("/conversation/<conversation_id>/summary", methods=["POST"])
def create_conversation_summary(conversation_id: str):
    """Create a summary of a conversation.
    
    This demonstrates how you might use NexaMem to store conversation summaries.
    """
    try:
        data = request.get_json()
        summary_content = data.get("summary", "")
        
        if not summary_content:
            return jsonify({"error": "Missing 'summary' in request body"}), 400
        
        # Store summary as a special turn
        summary_id = asyncio.run(app.memory_service.store_turn(
            conversation_id=conversation_id,
            content=summary_content,
            metadata={
                "type": "summary",
                "timestamp": time.time(),
                "created_by": "system",
                "source": "flask_app"
            }
        ))
        
        return jsonify({
            "success": True,
            "summary_id": summary_id,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to create conversation summary: {str(e)}"
        }), 500


if __name__ == "__main__":
    # Development server configuration
    print("Starting Flask NexaMem Integration Example")
    print("Available endpoints:")
    print("  POST /conversation/<id>/turn - Add conversation turn")
    print("  GET  /conversation/<id>/history - Get conversation history")
    print("  GET  /conversations/search?q=<query> - Search conversations")
    print("  POST /conversation/<id>/summary - Create conversation summary")
    print("  GET  /health - Health check")
    
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "true").lower() == "true"
    )