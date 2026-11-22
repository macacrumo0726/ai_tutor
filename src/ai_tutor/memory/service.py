from __future__ import annotations
import re

from .contextualizer import contextualize, format_history


class ConversationMemory:
    def __init__(self, repository, recent_messages=8, summarize_after=12, summary_max_chars=1600):
        self.repository = repository
        self.recent_messages = int(recent_messages)
        self.summarize_after = int(summarize_after)
        self.summary_max_chars = int(summary_max_chars)

    def create(self, user_id, **settings):
        return self.repository.create_conversation(user_id, **settings)

    def prepare(self, user_id, conversation_id, message):
        conversation = self.repository.get_conversation(user_id, conversation_id)
        messages = self.repository.list_messages(user_id, conversation_id)
        return {
            "conversation": conversation,
            "messages": messages,
            "retrieval_query": contextualize(message, messages, conversation.active_problem),
            "conversation_context": format_history(
                conversation.summary, conversation.active_problem, messages, self.recent_messages,
                conversation.pedagogical_state,
            ),
        }

    def record_turn(self, user_id, conversation_id, question, answer, metadata=None):
        self.repository.add_message(user_id, conversation_id, "user", question)
        self.repository.add_message(user_id, conversation_id, "assistant", answer, metadata)
        conversation = self.repository.get_conversation(user_id, conversation_id)
        values = {}
        if conversation.title == "Nueva conversación":
            values["title"] = self._title(question)
        active = self._active_problem(question)
        if active:
            values["active_problem"] = active
        messages = self.repository.list_messages(user_id, conversation_id)
        if len(messages) > self.summarize_after:
            values["summary"] = self._summarize(messages[:-self.recent_messages], conversation)
        if metadata:
            values.update({key: metadata[key] for key in ("retrieval_method", "model_provider", "student_profile", "pedagogical_state") if key in metadata})
        if values:
            self.repository.update_conversation(user_id, conversation_id, **values)
        return self.repository.get_conversation(user_id, conversation_id, with_messages=True)

    def chat_history(self, user_id, conversation_id):
        messages = self.repository.list_messages(user_id, conversation_id)
        history = []
        pending = None
        for message in messages:
            if message.role == "user":
                if pending is not None:
                    history.append((pending, ""))
                pending = message.content
            elif message.role == "assistant":
                history.append((pending or "", message.content)); pending = None
        if pending is not None:
            history.append((pending, ""))
        return history

    def _summarize(self, messages, conversation=None):
        """Create a compact, auditable summary without another LLM call.

        The summary is a control artifact, not a replacement for the transcript:
        it records the active topic and unresolved pedagogical state, then keeps
        short excerpts for traceability.
        """
        snippets = []
        if conversation is not None:
            if conversation.active_problem:
                snippets.append(f"Tema activo: {conversation.active_problem[:240]}")
            state = conversation.pedagogical_state or {}
            if state.get("current_activity"):
                snippets.append(f"Actividad: {state['current_activity']}")
            if state.get("pending_question"):
                snippets.append(f"Pregunta pendiente: {state['pending_question'][:240]}")
        for message in messages[-10:]:
            content = re.sub(r"\s+", " ", message.content).strip()
            snippets.append(f"{message.role}: {content[:220]}")
        return " | ".join(snippets)[-self.summary_max_chars:]

    @staticmethod
    def _title(question):
        compact = re.sub(r"\s+", " ", question).strip(" ¿?")
        return compact[:60] + ("…" if len(compact) > 60 else "")

    @staticmethod
    def _active_problem(question):
        topic_terms = re.search(
            r"\b(?:ecuaci[oó]n\w*|funci[oó]n\w*|dominio|rango|factoriz\w*|polinom\w*|trigonom\w*|desigualdad\w*|logarit\w*|exponent\w*|radical\w*|par[aá]bola\w*|sistema lineal|pendiente|matriz\w*|escalar\w*|producto punto|vector\w*|suma|resta|recta\w*|vertical|horizontal)\b",
            question,
            re.IGNORECASE,
        )
        words = re.findall(r"\w+", question, re.UNICODE)
        if any(symbol in question for symbol in ("=", "√", "/", "²", "^", "f(")) or (topic_terms and len(words) >= 4):
            return re.sub(r"\s+", " ", question).strip()[:500]
        return ""
