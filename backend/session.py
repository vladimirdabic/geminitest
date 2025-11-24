from dataclasses import dataclass
from google.genai import chats, Client, types
from typing import Dict
import time


@dataclass
class Session:
    last_access: float
    chat: chats.Chat
    instructions: str = None

class SessionStorage:
    sessions: Dict[str, Session]
    client: Client
    ttl: float

    def __init__(self, client: Client, ttl: float = 86400):
        self.sessions = {}
        self.client = client
        self.ttl = ttl

    def get_or_new(self, session_id: str, instructions: str = None) -> Session:
        self._cleanup()

        if session_id in self.sessions:
            return self.sessions[session_id]

        # TODO: Better model selection handling
        chat = self.client.chats.create(
            model='gemini-2.5-flash',
            config=types.GenerateContentConfig(
                system_instruction=instructions
            ) if instructions is not None else None
        )
        session = Session(last_access=time.time(), chat=chat, instructions=instructions)
        self.sessions[session_id] = session
        
        return session

    def _cleanup(self):
        now = time.time()
        expired = [id for id, session in self.sessions.items() if now - session.last_access > self.ttl]

        for id in expired:
            del self.sessions[id]