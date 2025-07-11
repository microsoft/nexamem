import uuid
from datetime import datetime


class ChatHistory:
    """
    Stores and manages LLM chatbot conversation history.
    """
    def __init__(self):
        self._history = []

    def add_message(self, role: str, content: str, **kwargs):
        """
        Add a message to the chat history.
        
        Args:
            role: Message role (e.g., 'user', 'assistant', 'system')
            content: Message content
            **kwargs: Additional properties (agent_id, user_id, session_id, env, tokens, data)
        """
        message = {
            "role": role,
            "content": content,
            "agent_id": kwargs.get("agent_id", ""),
            "user_id": kwargs.get("user_id", ""),
            "session_id": kwargs.get("session_id", str(uuid.uuid4())),
            "env": kwargs.get("env", "prod"),
            "timestamp": kwargs.get("timestamp", datetime.now().isoformat()),
            "tokens": kwargs.get("tokens", 0),
            "data": kwargs.get("data", "")
        }
        self._history.append(message)

    def get_history(self):
        return self._history.copy()

    def clear(self):
        self._history.clear()
