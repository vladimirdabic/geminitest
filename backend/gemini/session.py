from __future__ import annotations
from functools import wraps
from dataclasses import dataclass
from google.genai import chats, Client, types
from typing import Dict, List, Optional, Tuple, Callable
import time


DEFAULT_VALIDATOR_PROMPT = """Evaluate this AI response to the user's question:
            
USER QUESTION: {message}
AI RESPONSE: {response}
                    
Provide specific, constructive feedback and a quality score according to the structure you were instructed to.
"""

def validator(id: str, for_session: Session, validator_session: Session, prompt: str = DEFAULT_VALIDATOR_PROMPT):
    def decorator(func):
        if not any(existing.session == validator_session or existing.id == id for existing in for_session.validators):
            for_session.validators.append(Validator(
                id=id,
                session=validator_session,
                prompt=prompt,
                validate_func=func
            ))

        return func
    return decorator

@dataclass
class Validator:
    id: str
    session: Session
    prompt: str
    validate_func: Callable[
        [chats.GenerateContentResponse, chats.GenerateContentResponse, str],
        Tuple[Optional[str], Optional[object]]
    ]

@dataclass
class Session:
    last_access: float
    chat: chats.Chat
    instructions: Optional[str] = None
    validators: Optional[List[Validator]] = None

    def __post_init__(self):
        if self.validators is None:
            self.validators = []

    def send_message(self, message: str) -> Tuple[chats.GenerateContentResponse, Dict[str, object]]:
        response = self.chat.send_message(message=message)
        validator_data = {}

        if len(self.validators) != 0:
            for validator in self.validators:
                # TODO: Multithreading i cekati da se svi zavrse, pa zatim napraviti
                # prompt sa svim zajednickim feedbackom i poslati nazad
                resp, _ = validator.session.send_message(message=validator.prompt.format(message=message, response=response.text))

                correction_prompt, data = validator.validate_func(resp, response, message)
                validator_data[validator.id] = data

                if correction_prompt is not None:
                    response = self.chat.send_message(message=correction_prompt)

        #print(validator_data, self.validators)
        return response, validator_data

class SessionStorage:
    sessions: Dict[str, Session]
    client: Client
    ttl: float

    def __init__(self, api_key: str = None, client: Client = None, ttl: float = 86400):
        self.sessions = {}
        self.ttl = ttl
        
        if api_key is not None:
            self.client = Client(api_key=api_key)
        elif client is not None:
            self.client = client

    def get_or_new(self, session_id: str, instructions: str = None, agent_type: str = "expert") -> Session:
        self._cleanup()
        agent_session_id = f"{session_id}_{agent_type}"

        if agent_session_id in self.sessions:
            self.sessions[agent_session_id].last_access = time.time()
            return self.sessions[agent_session_id]

        # TODO: Better model selection handling
        chat = self.client.chats.create(
            model='gemini-2.5-flash',
            config=types.GenerateContentConfig(
                system_instruction=instructions
            ) if instructions is not None else None
        )
        session = Session(last_access=time.time(), chat=chat, instructions=instructions)
        self.sessions[agent_session_id] = session
        
        return session

    def _cleanup(self):
        now = time.time()
        expired = [id for id, session in self.sessions.items() if now - session.last_access > self.ttl]

        for id in expired:
            del self.sessions[id]