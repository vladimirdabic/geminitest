from __future__ import annotations
from dataclasses import dataclass
from google.genai import chats, Client, types
from typing import Dict, List, Optional, Tuple, Callable
from queue import Queue
import threading
import time


DEFAULT_VALIDATOR_PROMPT = """Evaluate this AI response to the user's question:
            
USER QUESTION: {message}
AI RESPONSE: {response}
                    
Provide specific, constructive feedback and a quality score according to the structure you were instructed to.
"""

def validator(id: str, validates: Session, using: Session, prompt: str = DEFAULT_VALIDATOR_PROMPT):
    def decorator(func):
        if not any(existing.session == using or existing.id == id for existing in validates.validators):
            validates.validators.append(Validator(
                id=id,
                session=using,
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

        if not self.validators:
            return response, {}
        
        out_queue = Queue()
        threads = []

        for validator in self.validators:
            t = threading.Thread(
                target=self.__run_validator_thread,
                args=(validator, message, response, out_queue)
            )

            threads.append(t)
            t.start()

        # Cekanje svih validatora
        for t in threads:
            t.join()
            
        corrections = []
        validator_data = {}

        while not out_queue.empty():
            vid, correction_prompt, data = out_queue.get()
            validator_data[vid] = data

            if correction_prompt is not None:
                corrections.append(correction_prompt)

        if corrections:
            master_prompt = (
                "Multiple reviewers have provided feedback:\n\n" +
                "\n\n".join(corrections) +
                "\n\nPlease revise your previous answer accordingly."
            )
            response = self.chat.send_message(master_prompt)

        return response, validator_data
    
    def __run_validator_thread(self, validator: Validator, message: str, response: chats.GenerateContentResponse, out_queue: Queue):
        prompt = validator.prompt.format(message=message, response=response.text)
        validator_resp, _ = validator.session.send_message(prompt)

        correction_prompt, data = validator.validate_func(
            validator_resp,
            response,
            message
        )

        out_queue.put((validator.id, correction_prompt, data))

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

    def get_or_new(self, session_id: str, instructions: str = None, session_label: str = "expert") -> Session:
        self._cleanup()
        agent_session_id = f"{session_id}_{session_label}"

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