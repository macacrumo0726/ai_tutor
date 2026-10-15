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
                conversation.summary, conversation.active_problem, messages, self.recent_messages
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
            values["summary"] = self._summarize(messages[:-self.recent_messages])
        if metadata:
            values.update({key: metadata[key] for key in ("retrieval_method", "model_provider", "student_profile") if key in metadata})
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

    def _summarize(self, messages):
        # Deterministic extractive summary: no extra API call and no hidden model variance.
        snippets = []
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
        if any(symbol in question for symbol in ("=", "√", "/", "²", "^", "f(")):
            return re.sub(r"\s+", " ", question).strip()[:500]
        return ""
