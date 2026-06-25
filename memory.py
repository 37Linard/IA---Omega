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
CHROMA_DIR  = os.path.join(os.path.dirname(__file__), "workspace", "chroma_db")

from config import OBSIDIAN_BASE
OBSIDIAN_SESSIONS_DIR = os.path.join(OBSIDIAN_BASE, "Agente IA", "Sessões")

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Índice vetorial — degradação graciosa se ChromaDB falhar
# ---------------------------------------------------------------------------
class VectorIndex:
    def __init__(self, persist_dir: str):
        self._ok = False
        try:
            import chromadb
            os.makedirs(persist_dir, exist_ok=True)
            self._client   = chromadb.PersistentClient(path=persist_dir)
            self._sessions = self._client.get_or_create_collection("sessions")
            self._facts    = self._client.get_or_create_collection("facts")
            self._ok       = True
            log.info("VectorIndex: ChromaDB OK em %s", persist_dir)
        except Exception as e:
            log.warning("VectorIndex: ChromaDB indisponível — %s", e)

    # ------------------------------------------------------------------
    def _safe_n(self, collection, n: int) -> int:
        count = collection.count()
        return min(n, count) if count > 0 else 0

    # ------------------------------------------------------------------
    def add_session(self, sid: str, task: str, result: str, timestamp: str):
        if not self._ok:
            return
        try:
            self._sessions.upsert(
                ids=[sid],
                documents=[f"{task}\n{result}"],
                metadatas=[{"task": task[:300], "result": result[:500], "ts": timestamp}],
            )
        except Exception as e:
            log.warning("VectorIndex.add_session: %s", e)

    def add_fact(self, fid: str, text: str, created: str):
        if not self._ok:
            return
        try:
            self._facts.upsert(
                ids=[fid],
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
            res = self._sessions.query(query_texts=[query], n_results=k)
            return res.get("metadatas", [[]])[0]
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
            res = self._facts.query(query_texts=[query], n_results=k)
            return res.get("metadatas", [[]])[0]
        except Exception as e:
            log.warning("VectorIndex.search_facts: %s", e)
            return []


class Memory:
    def __init__(self):
        self.data  = self._load()
        self.index = VectorIndex(CHROMA_DIR)
        self._sync_index()  # indexa dados existentes se index estiver vazio

    def _load(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "facts": []}

    def _sync_index(self):
        """Indexa sessões e fatos existentes no JSON que ainda não estão no ChromaDB."""
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
                    text = f.get("text", f) if isinstance(f, dict) else f
                    created = f.get("created", "") if isinstance(f, dict) else ""
                    self.index.add_fact(f"f{i}", text, created)
        except Exception as e:
            log.warning("_sync_index: %s", e)

    def _save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def save_session(self, task: str, result: str, scratchpad: list):
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

    def _export_to_obsidian(self, session: dict, scratchpad: list):
        try:
            ts = session["timestamp"][:16].replace("T", " ")
            date_prefix = session["timestamp"][:10]

            safe_title = re.sub(r'[<>:"/\\|?*]', '', session["task"])[:60].strip()
            filename = f"{date_prefix} — {safe_title}.md"
            filepath = os.path.join(OBSIDIAN_SESSIONS_DIR, filename)

            # Conflito no mesmo dia: adiciona hora
            if os.path.exists(filepath):
                hour_suffix = session["timestamp"][11:16].replace(":", "h")
                filename = f"{date_prefix} — {safe_title} ({hour_suffix}).md"
                filepath = os.path.join(OBSIDIAN_SESSIONS_DIR, filename)

            scratchpad_section = ""
            if scratchpad:
                steps_text = "\n---\n".join(str(s) for s in scratchpad[:10])
                scratchpad_section = f"\n## Raciocínio\n\n```\n{steps_text}\n```\n"

            note = (
                f"---\n"
                f"criado: {ts}\n"
                f"tags: [agente-ia, sessão]\n"
                f"steps: {session['steps']}\n"
                f"---\n\n"
                f"# {session['task']}\n\n"
                f"**Data:** {ts}  \n"
                f"**Steps:** {session['steps']}\n\n"
                f"## Resultado\n\n"
                f"{session['result']}\n"
                f"{scratchpad_section}"
            )

            os.makedirs(OBSIDIAN_SESSIONS_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(note)
        except Exception:
            pass  # export opcional — nunca quebra o agente

    def _backup(self):
        """Cria backup diário — mantém os últimos MAX_BACKUPS dias."""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            os.makedirs(BACKUP_DIR, exist_ok=True)
            dest = os.path.join(BACKUP_DIR, f"agent_memory_{today}.json")
            if not os.path.exists(dest):
                shutil.copy2(MEMORY_FILE, dest)
                # Remove backups antigos além do limite
                backups = sorted(
                    f for f in os.listdir(BACKUP_DIR) if f.startswith("agent_memory_")
                )
                for old in backups[:-MAX_BACKUPS]:
                    os.unlink(os.path.join(BACKUP_DIR, old))
        except Exception:
            pass

    def _prune_facts(self):
        """Remove fatos com mais de FACT_TTL_DAYS dias."""
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

    def get_context(self, task: str = "") -> str:
        self._prune_facts()
        if not self.data["sessions"] and not self.data["facts"]:
            return ""

        lines = ["=== MEMÓRIA DO AGENTE ==="]

        # Busca semântica se task fornecida, senão usa recentes
        if task and self.index._ok:
            relevant_facts    = self.index.search_facts(task, n=5)
            relevant_sessions = self.index.search_sessions(task, n=3)

            if relevant_facts:
                lines.append("\nFatos relevantes para esta tarefa:")
                for f in relevant_facts:
                    text = f.get("text", "")
                    age  = f.get("created", "")[:10]
                    lines.append(f"  - {text}" + (f" ({age})" if age else ""))

            if relevant_sessions:
                lines.append("\nTarefas similares anteriores:")
                for s in relevant_sessions:
                    lines.append(f"  [{s.get('ts', '')[:10]}] {s.get('task', '')[:80]}")
                    lines.append(f"    Resultado: {s.get('result', '')[:100]}")
        else:
            # Fallback: exibe tudo (comportamento original)
            if self.data["facts"]:
                lines.append("\nFatos importantes:")
                for f in self.data["facts"]:
                    text = f.get("text", f) if isinstance(f, dict) else f
                    age  = f.get("created", "")[:10] if isinstance(f, dict) else ""
                    lines.append(f"  - {text}" + (f" ({age})" if age else ""))

            if self.data["sessions"]:
                lines.append("\nÚltimas tarefas executadas:")
                for s in self.data["sessions"][-5:]:
                    lines.append(f"  [{s['timestamp'][:10]}] {s['task'][:80]}")
                    lines.append(f"    Resultado: {s['result'][:100]}")

        lines.append("=========================\n")
        return "\n".join(lines)
