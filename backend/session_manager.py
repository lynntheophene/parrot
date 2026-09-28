import uuid
import time
import threading


class SessionManager:

    def __init__(self, max_sessions=5):
        self.sessions = {}
        self.max_sessions = max_sessions
        self.lock = threading.Lock()


    def create_session(self):

        with self.lock:

            if len(self.sessions) >= self.max_sessions:
                return None

            session_id = str(uuid.uuid4())

            self.sessions[session_id] = {
                "created": time.time(),
                "history": []
            }

            print(
                f"New session: {session_id}"
            )

            return session_id


    def get_session(self, session_id):

        return self.sessions.get(session_id)


    def delete_session(self, session_id):

        with self.lock:

            if session_id in self.sessions:
                del self.sessions[session_id]

                print(
                    f"Deleted session: {session_id}"
                )


    def active_count(self):

        return len(self.sessions)

    def add_message(self, session_id, role, content):

        session = self.sessions.get(session_id)

        if session:
            session["history"].append(
                {
                    "role": role,
                    "content": content
                }
            )


    def get_history(self, session_id):

        session = self.sessions.get(session_id)

        if session:
            return session["history"]

        return []