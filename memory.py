import json
import logging
import os
import re
import shutil
from datetime import datetime, timedelta

BACKUP_DIR  = os.path.join(os.path.dirname(__file__), "workspace", "backups")
MAX_BACKUPS = 7
FACT_TTL_DAYS = 30

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "agent_memory.json")
LANCE_MEMORY_DIR = os.path.join(os.path.dirname(__file__), "workspace", "lance_memory_db")

from config import OBSIDIAN_BASE, REDIS_URL, SHORT_TERM_TTL, SHORT_TERM_MSGS
OBSIDIAN_SESSIONS_DIR = os.path.join(OBSIDIAN_BASE, "Agente IA", "Sessões")

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Short-Term Memory — Redis (TTL) com fallback dict
# ---------------------------------------------------------------------------
class ShortTermMemory:
    """Contexto imediato por sessão. Redis com graceful fallback para dict."""

    def __init__(self, ttl: int = SHORT_TERM_TTL, max_msgs: int = SHORT_TERM_MSGS):
        self.ttl      = ttl
        self.max_msgs = max_msgs
        self._redis   = None
        self._local: dict[str, list] = {}
        try:
            import redis as _redis
            r = _redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=2)
            r.ping()
            self._redis = r
            log.info("ShortTermMemory: Redis OK em %s", REDIS_URL)
        except Exception as e:
            log.info("ShortTermMemory: Redis indisponível (%s) — usando dict local", e)

    def add_message(self, session_id: str, role: str, content: str):
        if not session_id:
            return
        msg = json.dumps({"role": role, "content": content[:800]})
        key = f"sess:{session_id}:msgs"
        if self._redis:
            try:
                self._redis.rpush(key, msg)
                self._redis.ltrim(key, -self.max_msgs, -1)
                self._redis.expire(key, self.ttl)
                return
            except Exception as e:
                log.debug("ShortTermMemory.add_message redis: %s", e)
        msgs = self._local.setdefault(session_id, [])
        msgs.append({"role": role, "content": content[:800]})
        self._local[session_id] = msgs[-self.max_msgs:]

    def get_messages(self, session_id: str) -> list[dict]:
        if not session_id:
            return []
        key = f"sess:{session_id}:msgs"
        if self._redis:
            try:
                raw = self._redis.lrange(key, 0, -1)
                return [json.loads(m) for m in raw]
            except Exception as e:
                log.debug("ShortTermMemory.get_messages redis: %s", e)
        return self._local.get(session_id, [])

    def get_context(self, session_id: str) -> str:
        msgs = self.get_messages(session_id)
        if not msgs:
            return ""
        lines = ["=== CONVERSA RECENTE ==="]
        for m in msgs[-6:]:
            role = "Usuário" if m["role"] == "user" else "Agente"
            lines.append(f"  {role}: {m['content'][:200]}")
        lines.append("========================\n")
        return "\n".join(lines)

    def clear(self, session_id: str):
        if self._redis:
            try:
                self._redis.delete(f"sess:{session_id}:msgs")
                return
            except Exception:
                pass
        self._local.pop(session_id, None)


# ---------------------------------------------------------------------------
# Vector Index — LanceDB (serverless, embutido) + embeddings.get_embedder()
# ---------------------------------------------------------------------------
class VectorIndex:
    def __init__(self, persist_dir: str):
        self._ok       = False
        self._embed_fn = None
        try:
            import vector_store
            from embeddings import get_embedder

            os.makedirs(persist_dir, exist_ok=True)
            self._embed_fn, dim, kind = get_embedder()
            db = vector_store.connect(persist_dir)

            self._sessions = vector_store.LanceCollection(db, "sessions", dim)
            self._facts    = vector_store.LanceCollection(db, "facts", dim)
            self._ok = True
            log.info("VectorIndex: LanceDB OK em %s (embeddings=%s, dim=%d)", persist_dir, kind, dim)
        except Exception as e:
            log.warning("VectorIndex: LanceDB indisponível — %s", e)

    def _safe_n(self, collection, n: int) -> int:
        count = collection.count()
        return min(n, count) if count > 0 else 0

    def add_session(self, sid: str, task: str, result: str, timestamp: str):
        if not self._ok:
            return
        try:
            vec = self._embed_fn([f"{task}\n{result}"])[0]
            self._sessions.upsert(
                ids=[sid],
                vectors=[vec],
                documents=[f"{task}\n{result}"],
                metadatas=[{"task": task[:300], "result": result[:500], "ts": timestamp}],
            )
        except Exception as e:
            log.warning("VectorIndex.add_session: %s", e)

    def add_fact(self, fid: str, text: str, created: str):
        if not self._ok:
            return
        try:
            vec = self._embed_fn([text])[0]
            self._facts.upsert(
                ids=[fid],
                vectors=[vec],
                documents=[text],
                metadatas=[{"text": text, "created": created}],
            )
        except Exception as e:
            log.warning("VectorIndex.add_fact: %s", e)

    def delete_fact(self, fid: str):
        if not self._ok:
            return
        try:
            self._facts.delete(ids=[fid])
        except Exception:
            pass

    def search_sessions(self, query: str, n: int = 3) -> list[dict]:
        if not self._ok:
            return []
        k = self._safe_n(self._sessions, n)
        if k == 0:
            return []
        try:
            vec = self._embed_fn([query])[0]
            hits = self._sessions.query(vec, k)
            return [h["metadata"] for h in hits]
        except Exception as e:
            log.warning("VectorIndex.search_sessions: %s", e)
            return []

    def search_facts(self, query: str, n: int = 5) -> list[dict]:
        if not self._ok:
            return []
        k = self._safe_n(self._facts, n)
        if k == 0:
            return []
        try:
            vec = self._embed_fn([query])[0]
            hits = self._facts.query(vec, k)
            return [h["metadata"] for h in hits]
        except Exception as e:
            log.warning("VectorIndex.search_facts: %s", e)
            return []


# ---------------------------------------------------------------------------
# Memory — orquestra Short-Term + VectorIndex + KnowledgeGraph
# ---------------------------------------------------------------------------
class Memory:
    def __init__(self):
        self.data       = self._load()
        self.index      = VectorIndex(LANCE_MEMORY_DIR)
        self.short_term = ShortTermMemory()
        self._sync_index()

        # Knowledge graph — carregado lazy para não atrasar startup
        self._kg = None

    @property
    def kg(self):
        if self._kg is None:
            from knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph()
        return self._kg

    def _load(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "facts": []}

    def _sync_index(self):
        """Indexa sessões e fatos existentes que ainda não estão no ChromaDB."""
        if not self.index._ok:
            return
        try:
            if self.index._sessions.count() == 0:
                for i, s in enumerate(self.data.get("sessions", [])):
                    self.index.add_session(
                        f"s{i}", s.get("task", ""), s.get("result", ""), s.get("timestamp", "")
                    )
            if self.index._facts.count() == 0:
                for i, f in enumerate(self.data.get("facts", [])):
                    text    = f.get("text", f) if isinstance(f, dict) else f
                    created = f.get("created", "") if isinstance(f, dict) else ""
                    self.index.add_fact(f"f{i}", text, created)
        except Exception as e:
            log.warning("_sync_index: %s", e)

    def _save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def save_session(self, task: str, result: str, scratchpad: list, session_id: str = ""):
        ts = datetime.now().isoformat()
        session = {
            "timestamp": ts,
            "task":      task,
            "result":    result,
            "steps":     len(scratchpad),
        }
        self.data["sessions"].append(session)
        self.data["sessions"] = self.data["sessions"][-20:]
        self._save()
        self._backup()
        sid = f"s{len(self.data['sessions']) - 1}_{ts[:10]}"
        self.index.add_session(sid, task, result, ts)
        self._export_to_obsidian(session, scratchpad)

        # Salva no short-term
        if session_id:
            self.short_term.add_message(session_id, "user", task)
            self.short_term.add_message(session_id, "assistant", result)

        # Extrai entidades para knowledge graph em background
        combined = f"Pergunta: {task}\nResposta: {result}"
        import threading
        threading.Thread(
            target=lambda: self.kg._extract(combined, None),  # sem LLM — só armazena
            daemon=True
        ).start()

    def save_session_with_llm(self, task: str, result: str, scratchpad: list, llm, session_id: str = ""):
        """Igual a save_session mas extrai knowledge graph com LLM."""
        self.save_session(task, result, scratchpad, session_id)
        combined = f"Pergunta: {task}\nResposta: {result}"
        self.kg.extract_async(combined, llm)

    def _export_to_obsidian(self, session: dict, scratchpad: list):
        try:
            ts         = session["timestamp"][:16].replace("T", " ")
            date_prefix = session["timestamp"][:10]
            safe_title  = re.sub(r'[<>:"/\\|?*]', '', session["task"])[:60].strip()
            filename    = f"{date_prefix} — {safe_title}.md"
            filepath    = os.path.join(OBSIDIAN_SESSIONS_DIR, filename)

            if os.path.exists(filepath):
                hour_suffix = session["timestamp"][11:16].replace(":", "h")
                filename    = f"{date_prefix} — {safe_title} ({hour_suffix}).md"
                filepath    = os.path.join(OBSIDIAN_SESSIONS_DIR, filename)

            scratchpad_section = ""
            if scratchpad:
                steps_text = "\n---\n".join(str(s) for s in scratchpad[:10])
                scratchpad_section = f"\n## Raciocínio\n\n```\n{steps_text}\n```\n"

            note = (
                f"---\ncriado: {ts}\ntags: [agente-ia, sessão]\n"
                f"steps: {session['steps']}\n---\n\n"
                f"# {session['task']}\n\n**Data:** {ts}  \n**Steps:** {session['steps']}\n\n"
                f"## Resultado\n\n{session['result']}\n{scratchpad_section}"
            )
            os.makedirs(OBSIDIAN_SESSIONS_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(note)
        except Exception:
            pass

    def _backup(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            os.makedirs(BACKUP_DIR, exist_ok=True)
            dest = os.path.join(BACKUP_DIR, f"agent_memory_{today}.json")
            if not os.path.exists(dest):
                shutil.copy2(MEMORY_FILE, dest)
                backups = sorted(
                    f for f in os.listdir(BACKUP_DIR) if f.startswith("agent_memory_")
                )
                for old in backups[:-MAX_BACKUPS]:
                    os.unlink(os.path.join(BACKUP_DIR, old))
        except Exception:
            pass

    def _prune_facts(self):
        cutoff = (datetime.now() - timedelta(days=FACT_TTL_DAYS)).isoformat()
        kept = []
        for f in self.data["facts"]:
            if isinstance(f, dict):
                if f.get("created", "") >= cutoff:
                    kept.append(f)
            else:
                kept.append({"text": f, "created": datetime.now().isoformat()})
        self.data["facts"] = kept

    def save_fact(self, fact: str):
        existing = [
            f.get("text", f) if isinstance(f, dict) else f
            for f in self.data["facts"]
        ]
        if fact not in existing:
            ts = datetime.now().isoformat()
            self.data["facts"].append({"text": fact, "created": ts})
            self._prune_facts()
            self._save()
            fid = f"f{len(self.data['facts']) - 1}_{ts[:10]}"
            self.index.add_fact(fid, fact, ts)

    def get_context(self, task: str = "", session_id: str = "") -> str:
        self._prune_facts()

        lines = []

        # 1. Contexto imediato (Redis / dict)
        st_ctx = self.short_term.get_context(session_id)
        if st_ctx:
            lines.append(st_ctx)

        # 2. Knowledge graph
        if task:
            kg_ctx = self.kg.get_context(task)
            if kg_ctx:
                lines.append(kg_ctx)

        # 3. Memória episódica / semântica (ChromaDB)
        if not self.data["sessions"] and not self.data["facts"]:
            if lines:
                lines.insert(0, "=== MEMÓRIA DO AGENTE ===")
                lines.append("=========================\n")
            return "\n".join(lines) if lines else ""

        ep_lines = ["=== MEMÓRIA DO AGENTE ==="]

        if task and self.index._ok:
            relevant_facts    = self.index.search_facts(task, n=5)
            relevant_sessions = self.index.search_sessions(task, n=3)

            if relevant_facts:
                ep_lines.append("\nFatos relevantes para esta tarefa:")
                for f in relevant_facts:
                    text = f.get("text", "")
                    age  = f.get("created", "")[:10]
                    ep_lines.append(f"  - {text}" + (f" ({age})" if age else ""))

            if relevant_sessions:
                ep_lines.append("\nTarefas similares anteriores:")
                for s in relevant_sessions:
                    ep_lines.append(f"  [{s.get('ts', '')[:10]}] {s.get('task', '')[:80]}")
                    ep_lines.append(f"    Resultado: {s.get('result', '')[:100]}")
        else:
            if self.data["facts"]:
                ep_lines.append("\nFatos importantes:")
                for f in self.data["facts"]:
                    text = f.get("text", f) if isinstance(f, dict) else f
                    age  = f.get("created", "")[:10] if isinstance(f, dict) else ""
                    ep_lines.append(f"  - {text}" + (f" ({age})" if age else ""))

            if self.data["sessions"]:
                ep_lines.append("\nÚltimas tarefas executadas:")
                for s in self.data["sessions"][-5:]:
                    ep_lines.append(f"  [{s['timestamp'][:10]}] {s['task'][:80]}")
                    ep_lines.append(f"    Resultado: {s['result'][:100]}")

        ep_lines.append("=========================\n")
        lines.append("\n".join(ep_lines))

        return "\n".join(lines)
