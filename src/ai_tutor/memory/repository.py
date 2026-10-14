from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schema import Conversation, Message


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    """Small SQLite repository with explicit user/conversation isolation."""

    def __init__(self, database_path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(str(self.database_path), timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                password_salt TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'student'
            );
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                active_problem TEXT NOT NULL DEFAULT '',
                retrieval_method TEXT NOT NULL DEFAULT 'rag',
                model_provider TEXT NOT NULL DEFAULT 'instructional',
                student_profile TEXT NOT NULL DEFAULT 'unknown',
                archived INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_user_updated
                ON conversations(user_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
                ON messages(conversation_id, created_at);
            CREATE TABLE IF NOT EXISTS concept_mastery (
                user_id TEXT NOT NULL REFERENCES users(user_id),
                concept_id TEXT NOT NULL,
                mastery REAL NOT NULL,
                confidence REAL NOT NULL DEFAULT 0,
                evidence_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, concept_id)
            );
            CREATE TABLE IF NOT EXISTS student_profiles (
                user_id TEXT PRIMARY KEY REFERENCES users(user_id),
                default_mastery REAL NOT NULL DEFAULT 0.5,
                confidence REAL NOT NULL DEFAULT 0,
                evidence_count INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learning_evidence (
                evidence_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                conversation_id TEXT REFERENCES conversations(conversation_id),
                concept_id TEXT NOT NULL,
                evidence_type TEXT NOT NULL,
                outcome REAL NOT NULL,
                source TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_user_concept
                ON learning_evidence(user_id, concept_id, created_at);
            CREATE TABLE IF NOT EXISTS student_misconceptions (
                user_id TEXT NOT NULL REFERENCES users(user_id),
                concept_id TEXT NOT NULL,
                misconception TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'suspected',
                confidence REAL NOT NULL DEFAULT 0.5,
                evidence_count INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(user_id, concept_id, misconception)
            );
            CREATE TABLE IF NOT EXISTS learning_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                conversation_id TEXT REFERENCES conversations(conversation_id),
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_user_created
                ON learning_events(user_id, created_at);
            CREATE TABLE IF NOT EXISTS micro_checks (
                micro_check_id TEXT PRIMARY KEY,
                concept_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assessment_attempts (
                attempt_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                conversation_id TEXT REFERENCES conversations(conversation_id),
                micro_check_id TEXT NOT NULL REFERENCES micro_checks(micro_check_id),
                attempt_number INTEGER NOT NULL,
                answer TEXT NOT NULL,
                result_json TEXT NOT NULL,
                decision_json TEXT NOT NULL,
                mastery_before REAL NOT NULL,
                mastery_after REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_attempts_user_check
                ON assessment_attempts(user_id,micro_check_id,attempt_number);
            CREATE TABLE IF NOT EXISTS student_self_reports (
                self_report_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                conversation_id TEXT REFERENCES conversations(conversation_id),
                concept_ids_json TEXT NOT NULL,
                report TEXT NOT NULL,
                reported_score REAL NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS understanding_evaluations (
                evaluation_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(user_id),
                conversation_id TEXT REFERENCES conversations(conversation_id),
                concept_ids_json TEXT NOT NULL,
                student_message TEXT NOT NULL,
                classification TEXT NOT NULL,
                score REAL,
                confidence REAL NOT NULL,
                features_json TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_self_reports_user_created
                ON student_self_reports(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_understanding_user_created
                ON understanding_evaluations(user_id, created_at DESC);
            """)
            # Safe migrations for databases created by earlier versions.
            columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
            for name, definition in (
                ("password_hash", "TEXT NOT NULL DEFAULT ''"),
                ("password_salt", "TEXT NOT NULL DEFAULT ''"),
                ("role", "TEXT NOT NULL DEFAULT 'student'"),
            ):
                if name not in columns:
                    db.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")

    def ensure_user(self, user_id: str, display_name: Optional[str] = None):
        user_id = self.normalize_user_id(user_id)
        with self._connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO users(user_id,display_name,created_at) VALUES(?,?,?)",
                (user_id, display_name or user_id, _now()),
            )
        return user_id

    def get_user(self, user_id: str):
        user_id = self.normalize_user_id(user_id)
        with self._connect() as db:
            row = db.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        return dict(row) if row else None

    def set_credentials(self, user_id: str, display_name: str, password_hash: str,
                        password_salt: str, role: str = "student"):
        user_id = self.normalize_user_id(user_id)
        if role not in {"student", "researcher"}:
            raise ValueError("Invalid role")
        with self._connect() as db:
            existing = db.execute("SELECT password_hash FROM users WHERE user_id=?", (user_id,)).fetchone()
            if existing and existing["password_hash"]:
                raise ValueError("El usuario ya está registrado")
            db.execute("""INSERT INTO users(user_id,display_name,created_at,password_hash,password_salt,role)
                VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET
                display_name=excluded.display_name,password_hash=excluded.password_hash,
                password_salt=excluded.password_salt,role=excluded.role""",
                (user_id, display_name.strip()[:100] or user_id, _now(), password_hash, password_salt, role))
            db.execute("INSERT OR IGNORE INTO student_profiles(user_id,updated_at) VALUES(?,?)", (user_id, _now()))
        return self.get_user(user_id)

    def list_users(self):
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT user_id,display_name,role,created_at FROM users ORDER BY created_at DESC").fetchall()]

    def get_mastery(self, user_id: str):
        user_id = self.normalize_user_id(user_id)
        with self._connect() as db:
            rows = db.execute("SELECT * FROM concept_mastery WHERE user_id=? ORDER BY concept_id", (user_id,)).fetchall()
        return [dict(row) for row in rows]

    def get_student_profile(self, user_id: str):
        user_id = self.normalize_user_id(user_id)
        self.ensure_user(user_id)
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO student_profiles(user_id,updated_at) VALUES(?,?)", (user_id, _now()))
            row = db.execute("SELECT * FROM student_profiles WHERE user_id=?", (user_id,)).fetchone()
        return dict(row)

    def add_learning_evidence(self, user_id: str, concept_id: str, evidence_type: str,
                              outcome: float, source: str, conversation_id=None, metadata=None,
                              evidence_weight: float = 1.0):
        user_id = self.normalize_user_id(user_id)
        self.ensure_user(user_id)
        outcome = min(1.0, max(0.0, float(outcome)))
        evidence_id, timestamp = f"evd_{uuid.uuid4().hex}", _now()
        with self._connect() as db:
            previous = db.execute("SELECT * FROM concept_mastery WHERE user_id=? AND concept_id=?",
                                  (user_id, concept_id)).fetchone()
            old = float(previous["mastery"]) if previous else 0.5
            old_confidence = float(previous["confidence"]) if previous else 0.0
            count = int(previous["evidence_count"]) if previous else 0
            # Incremental evidence update: the first observation matters, later ones stabilize the estimate.
            evidence_weight = min(1.0, max(0.0, float(evidence_weight)))
            alpha = max(0.10, min(0.50, 1.0 / (count + 2))) * evidence_weight
            mastery = old + alpha * (outcome - old)
            new_count = count + 1
            confidence = old_confidence + evidence_weight * (1.0 - old_confidence) * 0.5
            db.execute("""INSERT INTO concept_mastery(user_id,concept_id,mastery,confidence,evidence_count,updated_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,concept_id) DO UPDATE SET
                mastery=excluded.mastery,confidence=excluded.confidence,
                evidence_count=excluded.evidence_count,updated_at=excluded.updated_at""",
                (user_id, concept_id, mastery, confidence, new_count, timestamp))
            db.execute("INSERT INTO learning_evidence VALUES(?,?,?,?,?,?,?,?,?)", (
                evidence_id, user_id, conversation_id, concept_id, evidence_type, outcome, source,
                json.dumps({**(metadata or {}), "evidence_weight": evidence_weight}, ensure_ascii=False), timestamp))
            total = db.execute("SELECT COUNT(*) AS n FROM learning_evidence WHERE user_id=?", (user_id,)).fetchone()["n"]
            avg_confidence = db.execute(
                "SELECT COALESCE(AVG(confidence),0) AS value FROM concept_mastery WHERE user_id=?", (user_id,)
            ).fetchone()["value"]
            db.execute("""UPDATE student_profiles SET evidence_count=?,confidence=?,updated_at=? WHERE user_id=?""",
                       (total, avg_confidence, timestamp, user_id))
        return {"concept_id": concept_id, "previous_mastery": old, "mastery": mastery,
                "confidence": confidence, "evidence_count": new_count, "alpha": alpha,
                "outcome": outcome, "evidence_weight": evidence_weight}

    def add_learning_event(self, user_id: str, event_type: str, payload=None, conversation_id=None):
        event_id = f"evt_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute("INSERT INTO learning_events VALUES(?,?,?,?,?,?)", (
                event_id, self.normalize_user_id(user_id), conversation_id, event_type,
                json.dumps(payload or {}, ensure_ascii=False), _now()))
        return event_id

    def learning_report(self, user_id: str):
        profile = self.get_student_profile(user_id)
        with self._connect() as db:
            evidence = [dict(row) for row in db.execute(
                "SELECT * FROM learning_evidence WHERE user_id=? ORDER BY created_at DESC", (self.normalize_user_id(user_id),)).fetchall()]
            misconceptions = [dict(row) for row in db.execute(
                "SELECT * FROM student_misconceptions WHERE user_id=? ORDER BY updated_at DESC", (self.normalize_user_id(user_id),)).fetchall()]
            self_reports = [dict(row) for row in db.execute(
                "SELECT * FROM student_self_reports WHERE user_id=? ORDER BY created_at DESC", (self.normalize_user_id(user_id),)).fetchall()]
            evaluations = [dict(row) for row in db.execute(
                "SELECT * FROM understanding_evaluations WHERE user_id=? ORDER BY created_at DESC", (self.normalize_user_id(user_id),)).fetchall()]
        return {"profile": profile, "mastery": self.get_mastery(user_id),
                "evidence": evidence, "misconceptions": misconceptions,
                "self_reports": self_reports, "understanding_evaluations": evaluations,
                "latest_signal_comparison": self.latest_signal_comparison(user_id)}

    def save_micro_check(self,payload):
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO micro_checks VALUES(?,?,?,?)",(
                payload["micro_check_id"],payload["concept_id"],json.dumps(payload,ensure_ascii=False),_now()))

    def next_attempt_number(self,user_id,micro_check_id):
        with self._connect() as db:
            row=db.execute("SELECT COUNT(*) AS n FROM assessment_attempts WHERE user_id=? AND micro_check_id=?",
                           (self.normalize_user_id(user_id),micro_check_id)).fetchone()
        return int(row["n"])+1

    def save_assessment_attempt(self,user_id,conversation_id,micro_check_id,answer,result,decision,
                                mastery_before,mastery_after):
        attempt_number=self.next_attempt_number(user_id,micro_check_id)
        attempt_id=f"att_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute("INSERT INTO assessment_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?)",(
                attempt_id,self.normalize_user_id(user_id),conversation_id,micro_check_id,
                attempt_number,answer,json.dumps(result,ensure_ascii=False),json.dumps(decision,ensure_ascii=False),
                float(mastery_before),float(mastery_after),_now()))
        return attempt_id

    def list_assessment_attempts(self,user_id):
        with self._connect() as db:
            return [dict(row) for row in db.execute(
                "SELECT * FROM assessment_attempts WHERE user_id=? ORDER BY created_at DESC",
                (self.normalize_user_id(user_id),)).fetchall()]

    def save_self_report(self,user_id,conversation_id,concept_ids,report,reported_score):
        report_id=f"sr_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute("INSERT INTO student_self_reports VALUES(?,?,?,?,?,?,?)",(
                report_id,self.normalize_user_id(user_id),conversation_id,
                json.dumps(list(concept_ids),ensure_ascii=False),report,float(reported_score),_now()))
        return report_id

    def save_understanding_evaluation(self,user_id,conversation_id,concept_ids,message,
                                      classification,score,confidence,features,source):
        evaluation_id=f"ue_{uuid.uuid4().hex}"
        with self._connect() as db:
            db.execute("INSERT INTO understanding_evaluations VALUES(?,?,?,?,?,?,?,?,?,?,?)",(
                evaluation_id,self.normalize_user_id(user_id),conversation_id,
                json.dumps(list(concept_ids),ensure_ascii=False),message,classification,
                score,float(confidence),json.dumps(features,ensure_ascii=False),source,_now()))
        return evaluation_id

    def latest_signal_comparison(self,user_id,conversation_id=None):
        user_id=self.normalize_user_id(user_id)
        condition="user_id=?"; params=[user_id]
        if conversation_id: condition+=" AND conversation_id=?"; params.append(conversation_id)
        with self._connect() as db:
            report=db.execute(f"SELECT * FROM student_self_reports WHERE {condition} ORDER BY created_at DESC LIMIT 1",params).fetchone()
            evaluation=db.execute(f"SELECT * FROM understanding_evaluations WHERE {condition} ORDER BY created_at DESC LIMIT 1",params).fetchone()
        if not report or not evaluation:return {"status":"insufficient_data"}
        if evaluation["score"] is None:
            return {"status":"evaluator_unscored","self_report":dict(report),
                    "evaluator":dict(evaluation)}
        self_score=float(report["reported_score"]); evaluator_score=float(evaluation["score"])
        gap=abs(self_score-evaluator_score)
        direction=("self_report_higher" if self_score>evaluator_score else
                   "evaluator_higher" if evaluator_score>self_score else "equal")
        return {"status":"agreement" if gap<=.25 else "contradiction","gap":round(gap,3),
                "direction":direction,"self_report":dict(report),"evaluator":dict(evaluation)}

    @staticmethod
    def normalize_user_id(value: str) -> str:
        cleaned = "".join(character for character in (value or "anonymous").strip().lower()
                          if character.isalnum() or character in "_-" )[:64]
        return cleaned or "anonymous"

    def create_conversation(self, user_id: str, title="Nueva conversación", **settings) -> Conversation:
        user_id = self.ensure_user(user_id)
        conversation_id = f"conv_{uuid.uuid4().hex}"
        timestamp = _now()
        with self._connect() as db:
            db.execute("""INSERT INTO conversations(
                conversation_id,user_id,title,created_at,updated_at,retrieval_method,model_provider,student_profile
            ) VALUES(?,?,?,?,?,?,?,?)""", (
                conversation_id, user_id, title[:120], timestamp, timestamp,
                settings.get("retrieval_method", "rag"), settings.get("model_provider", "instructional"),
                settings.get("student_profile", "unknown"),
            ))
        return self.get_conversation(user_id, conversation_id)

    def list_conversations(self, user_id: str, include_archived=False) -> list[Conversation]:
        user_id = self.ensure_user(user_id)
        query = "SELECT * FROM conversations WHERE user_id=?"
        params = [user_id]
        if not include_archived:
            query += " AND archived=0"
        query += " ORDER BY updated_at DESC"
        with self._connect() as db:
            return [self._conversation(row) for row in db.execute(query, params).fetchall()]

    def get_conversation(self, user_id: str, conversation_id: str, with_messages=False) -> Conversation:
        user_id = self.normalize_user_id(user_id)
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM conversations WHERE conversation_id=? AND user_id=?",
                (conversation_id, user_id),
            ).fetchone()
        if row is None:
            raise KeyError("Conversation not found for this user")
        conversation = self._conversation(row)
        if with_messages:
            conversation.messages = self.list_messages(user_id, conversation_id)
        return conversation

    def list_messages(self, user_id: str, conversation_id: str, limit=None) -> list[Message]:
        self.get_conversation(user_id, conversation_id)
        query = "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC"
        params = [conversation_id]
        if limit:
            query = "SELECT * FROM (SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?) ORDER BY created_at ASC"
            params.append(int(limit))
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        return [Message(row["message_id"], row["conversation_id"], row["role"], row["content"],
                        row["created_at"], json.loads(row["metadata_json"] or "{}")) for row in rows]

    def add_message(self, user_id: str, conversation_id: str, role: str, content: str, metadata=None) -> Message:
        self.get_conversation(user_id, conversation_id)
        message_id = f"msg_{uuid.uuid4().hex}"
        timestamp = _now()
        with self._connect() as db:
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?)", (
                message_id, conversation_id, role, content, timestamp,
                json.dumps(metadata or {}, ensure_ascii=False),
            ))
            db.execute("UPDATE conversations SET updated_at=? WHERE conversation_id=?", (timestamp, conversation_id))
        return Message(message_id, conversation_id, role, content, timestamp, metadata or {})

    def update_conversation(self, user_id: str, conversation_id: str, **values):
        self.get_conversation(user_id, conversation_id)
        allowed = {"title", "summary", "active_problem", "retrieval_method", "model_provider", "student_profile", "archived"}
        updates = {key: value for key, value in values.items() if key in allowed}
        if not updates:
            return self.get_conversation(user_id, conversation_id)
        updates["updated_at"] = _now()
        assignment = ",".join(f"{key}=?" for key in updates)
        with self._connect() as db:
            db.execute(f"UPDATE conversations SET {assignment} WHERE conversation_id=?", [*updates.values(), conversation_id])
        return self.get_conversation(user_id, conversation_id)

    @staticmethod
    def _conversation(row) -> Conversation:
        return Conversation(
            row["conversation_id"], row["user_id"], row["title"], row["created_at"], row["updated_at"],
            row["summary"], row["active_problem"], row["retrieval_method"], row["model_provider"],
            row["student_profile"], bool(row["archived"]),
        )
