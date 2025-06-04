class ChatHistory:
    """
    Stores and manages LLM chatbot conversation history.
    """
    def __init__(self):
        self._history = []

    def add_message(self, role: str, content: str):
        self._history.append({"role": role, "content": content})

    def get_history(self):
        return self._history.copy()

    def clear(self):
        self._history.clear()
