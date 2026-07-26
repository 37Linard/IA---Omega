import json
import logging
import os
import re
import shutil
import threading
import uuid
from datetime import datetime, timedelta

BACKUP_DIR  = os.path.join(os.path.dirname(__file__), "workspace", "backups")
MAX_BACKUPS = 7
FACT_TTL_DAYS = 30
MAX_FACTS = 200   # cap de armazenamento — sessions já é limitado a 20, facts não tinha teto
CONTEXT_MAX_FACTS = 15   # cap do que entra no prompt quando a busca semântica (LanceDB) está indisponível
CONTEXT_FACT_CHARS = 150
MAX_EPISODES = 50
EPISODE_MIN_MSGS = 2   # sessão com só 1 msg (ou 0) não vira episódio — nada pra resumir

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "agent_memory.json")
LANCE_MEMORY_DIR = os.path.join(os.path.dirname(__file__), "workspace", "lance_memory_db")
LEGACY_GRAPH_FILE = os.path.join(os.path.dirname(__file__), "workspace", "knowledge_graph.json")

from config import OBSIDIAN_BASE, REDIS_URL, SHORT_TERM_TTL, SHORT_TERM_MSGS, link_note_in_conversas_index
OBSIDIAN_SESSIONS_DIR = os.path.join(OBSIDIAN_BASE, "Gabriel", "Projetos", "Agente IA Local", "Conversas")

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
            self._episodes = vector_store.LanceCollection(db, "episodes", dim)
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

    def delete_session(self, sid: str):
        if not self._ok:
            return
        try:
            self._sessions.delete(ids=[sid])
        except Exception:
            pass

    def delete_episode(self, eid: str):
        if not self._ok:
            return
        try:
            self._episodes.delete(ids=[eid])
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

    def add_episode(self, eid: str, summary: str, timestamp: str):
        if not self._ok:
            return
        try:
            vec = self._embed_fn([summary])[0]
            self._episodes.upsert(
                ids=[eid],
                vectors=[vec],
                documents=[summary],
                metadatas=[{"summary": summary, "ts": timestamp}],
            )
        except Exception as e:
            log.warning("VectorIndex.add_episode: %s", e)

    def search_episodes(self, query: str, n: int = 3) -> list[dict]:
        if not self._ok:
            return []
        k = self._safe_n(self._episodes, n)
        if k == 0:
            return []
        try:
            vec = self._embed_fn([query])[0]
            hits = self._episodes.query(vec, k)
            return [h["metadata"] for h in hits]
        except Exception as e:
            log.warning("VectorIndex.search_episodes: %s", e)
            return []


# ---------------------------------------------------------------------------
# Memory — orquestra Short-Term + VectorIndex + KnowledgeGraph
# ---------------------------------------------------------------------------
class Memory:
    def __init__(self):
        self.data       = self._load()
        self.data.setdefault("episodes", [])
        self._migrate_legacy_kg()
        self.index      = VectorIndex(LANCE_MEMORY_DIR)
        self.short_term = ShortTermMemory()
        self._sync_index()

        # Knowledge graph — carregado lazy para não atrasar startup
        self._kg = None

    @property
    def kg(self):
        if self._kg is None:
            from knowledge_graph import KnowledgeGraph
            self._kg = KnowledgeGraph(self.data.setdefault("kg", {"entities": {}, "relations": []}), self._save)
        return self._kg

    def _load(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "facts": [], "episodes": []}

    def _migrate_legacy_kg(self):
        """workspace/knowledge_graph.json era um arquivo/lock/backup separado —
        unificado pra dentro de agent_memory.json (chave "kg"), 1x, na primeira
        carga depois do upgrade. Só roda se "kg" ainda não existe no JSON
        principal (idempotente) e o arquivo legado existe. Renomeia em vez de
        apagar (reversível) — dado real de produção, não é scratch."""
        if "kg" in self.data or not os.path.exists(LEGACY_GRAPH_FILE):
            return
        try:
            with open(LEGACY_GRAPH_FILE, "r", encoding="utf-8") as f:
                legacy = json.load(f)
            self.data["kg"] = {
                "entities": legacy.get("entities", {}),
                "relations": legacy.get("relations", []),
            }
            self._save()
            os.rename(LEGACY_GRAPH_FILE, LEGACY_GRAPH_FILE + ".migrated")
            log.info("Memory: knowledge_graph.json migrado pra agent_memory.json (kg), arquivo antigo renomeado .migrated")
        except Exception as e:
            log.warning("Memory._migrate_legacy_kg: %s", e)

    @staticmethod
    def _new_id(prefix: str) -> str:
        """ID estável e único (independe de posição na lista) — o esquema antigo
        usava índice+data (ex: 'f12_2026-07-23'), que colidia depois de qualquer
        prune/trim (posições são reaproveitadas), fazendo o upsert do LanceDB
        sobrescrever silenciosamente o fato/sessão/episódio errado."""
        return f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _trim(self, key: str, cap: int, id_prefix: str) -> list[str]:
        """Corta self.data[key] pros últimos `cap` itens, garantindo "id" estável
        em cada um (backfill preguiçoso pra dado legado sem essa chave) e
        retornando os ids que caíram fora — quem chama propaga pro delete do
        índice, senão o LanceDB acumula entrada órfã pra sempre."""
        items = self.data[key]
        for item in items:
            item.setdefault("id", self._new_id(id_prefix))
        if len(items) <= cap:
            return []
        removed_ids = [item["id"] for item in items[:-cap]]
        self.data[key] = items[-cap:]
        return removed_ids

    def _sync_index(self):
        """Indexa sessões/fatos/episódios existentes que ainda não estão no LanceDB."""
        if not self.index._ok:
            return
        try:
            # garante ids estáveis ANTES de indexar — dado legado sem "id" faria
            # todo mundo colidir em id="" no upsert (só o último sobreviveria)
            self._prune_facts()
            self._trim("sessions", 20, "s")
            self._trim("episodes", MAX_EPISODES, "e")
            self._save()

            if self.index._sessions.count() == 0:
                for s in self.data.get("sessions", []):
                    self.index.add_session(s["id"], s.get("task", ""), s.get("result", ""), s.get("timestamp", ""))
            if self.index._facts.count() == 0:
                for f in self.data.get("facts", []):
                    self.index.add_fact(f["id"], f.get("text", ""), f.get("created", ""))
            if self.index._episodes.count() == 0:
                for e in self.data.get("episodes", []):
                    self.index.add_episode(e["id"], e.get("summary", ""), e.get("timestamp", ""))
        except Exception as e:
            log.warning("_sync_index: %s", e)

    def _save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def save_session(self, task: str, result: str, scratchpad: list, session_id: str = ""):
        ts  = datetime.now().isoformat()
        sid = self._new_id("s")
        session = {
            "id":        sid,
            "timestamp": ts,
            "task":      task,
            "result":    result,
            "steps":     len(scratchpad),
        }
        self.data["sessions"].append(session)
        removed_ids = self._trim("sessions", 20, "s")
        self._save()
        self._backup()
        self.index.add_session(sid, task, result, ts)
        for rid in removed_ids:
            self.index.delete_session(rid)
        self._export_to_obsidian(session, scratchpad)

        # Salva no short-term
        if session_id:
            self.short_term.add_message(session_id, "user", task)
            self.short_term.add_message(session_id, "assistant", result)

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
            link_note_in_conversas_index(OBSIDIAN_SESSIONS_DIR, filename)
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

    def _prune_facts(self) -> list[str]:
        """Normaliza (dict + id estável, tolera fato legado como string crua),
        aplica TTL e cap de tamanho. Retorna os ids que caíram fora — quem
        chama propaga pro delete do índice (achado real: antes disso, fato
        podia expirar/ser cortado do JSON e continuar pra sempre pesquisável
        no LanceDB, órfão)."""
        cutoff = (datetime.now() - timedelta(days=FACT_TTL_DAYS)).isoformat()
        normalized = []
        for f in self.data["facts"]:
            if isinstance(f, dict):
                f.setdefault("id", self._new_id("f"))
                normalized.append(f)
            else:
                normalized.append({"id": self._new_id("f"), "text": f, "created": datetime.now().isoformat()})

        before_ids = {f["id"] for f in normalized}
        kept = [f for f in normalized if f.get("created", "") >= cutoff]
        kept = kept[-MAX_FACTS:]
        after_ids = {f["id"] for f in kept}

        self.data["facts"] = kept
        return sorted(before_ids - after_ids)

    def save_fact(self, fact: str):
        existing = [
            f.get("text", f) if isinstance(f, dict) else f
            for f in self.data["facts"]
        ]
        if fact not in existing:
            ts  = datetime.now().isoformat()
            fid = self._new_id("f")
            self.data["facts"].append({"id": fid, "text": fact, "created": ts})
            removed_ids = self._prune_facts()
            self._save()
            self.index.add_fact(fid, fact, ts)
            for rid in removed_ids:
                self.index.delete_fact(rid)

    # ------------------------------------------------------------------
    # Episódios — resumo de uma sessão de conversa inteira, pra recall
    # ("na sessão passada você pediu X") depois que o short-term (Redis,
    # TTL 1800s) já expirou ou a aba/conexão fechou.
    # ------------------------------------------------------------------
    def end_session(self, session_id: str, llm=None) -> None:
        """Chamado quando uma sessão de conversa termina (WS desconectou).
        Resume em background — não trava o encerramento da conexão."""
        if not session_id:
            return
        t = threading.Thread(target=self._end_session, args=(session_id, llm), daemon=True)
        t.start()

    def _end_session(self, session_id: str, llm=None) -> None:
        msgs = self.short_term.get_messages(session_id)
        if len(msgs) < EPISODE_MIN_MSGS:
            return

        summary = ""
        if llm:
            transcript = "\n".join(f"{m['role']}: {m['content'][:300]}" for m in msgs[-10:])
            prompt = (
                "Resuma em 1 frase curta (português, sem preâmbulo tipo 'A conversa foi...') "
                "o que o usuário pediu e o que foi feito nesta conversa:\n\n"
                f"{transcript}\n\nResumo:"
            )
            try:
                summary = llm.generate(prompt).strip()[:300]
            except Exception as e:
                log.debug("Memory._end_session summarize: %s", e)

        if not summary:
            first_user = next((m["content"] for m in msgs if m["role"] == "user"), "")
            summary = first_user[:200]
        if not summary:
            return

        ts  = datetime.now().isoformat()
        eid = self._new_id("e")
        self.data["episodes"].append({
            "id":            eid,
            "session_id":    session_id,
            "timestamp":     ts,
            "summary":       summary,
            "message_count": len(msgs),
        })
        removed_ids = self._trim("episodes", MAX_EPISODES, "e")
        self._save()
        self.index.add_episode(eid, summary, ts)
        for rid in removed_ids:
            self.index.delete_episode(rid)
        self.short_term.clear(session_id)

    def get_last_episode_context(self, exclude_session_id: str = "") -> str:
        episodes = [e for e in self.data.get("episodes", []) if e.get("session_id") != exclude_session_id]
        if not episodes:
            return ""
        last = episodes[-1]
        return (
            f"=== SESSÃO ANTERIOR ({self._time_ago(last['timestamp'])}) ===\n"
            f"{last['summary']}\n"
            f"================================\n"
        )

    def search_episodes(self, query: str, n: int = 3) -> list[dict]:
        """Busca semântica em resumos de sessões passadas (RAG sobre episódios).
        Sem LanceDB, degrada pra substring case-insensitive nos resumos mais recentes."""
        if self.index._ok:
            hits = self.index.search_episodes(query, n=n)
            if hits:
                return hits
        query_lower = query.lower()
        matches = [
            e for e in reversed(self.data.get("episodes", []))
            if query_lower in e.get("summary", "").lower()
        ]
        return matches[:n]

    @staticmethod
    def _time_ago(ts_iso: str) -> str:
        try:
            dt = datetime.fromisoformat(ts_iso)
        except Exception:
            return ts_iso[:10]
        secs = (datetime.now() - dt).total_seconds()
        if secs < 3600:
            return f"há {max(1, int(secs // 60))} min"
        if secs < 86400:
            return f"há {int(secs // 3600)}h"
        return f"há {int(secs // 86400)}d"

    def get_context(self, task: str = "", session_id: str = "") -> str:
        self._prune_facts()

        lines = []

        # 0. Recall da sessão anterior — só faz sentido na primeira mensagem
        # de uma sessão nova (short-term desta sessão ainda vazio)
        if session_id and not self.short_term.get_messages(session_id):
            recall = self.get_last_episode_context(exclude_session_id=session_id)
            if recall:
                lines.append(recall)

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
                # Fallback sem busca semântica (LanceDB indisponível) — sem isso o
                # prompt levava TODOS os fatos armazenados, sem truncar, estourando
                # NUM_CTX de forma silenciosa e imprevisível.
                recent_facts = self.data["facts"][-CONTEXT_MAX_FACTS:]
                ep_lines.append(
                    f"\nFatos importantes (mais recentes, {len(recent_facts)} de {len(self.data['facts'])}):"
                )
                for f in recent_facts:
                    text = f.get("text", f) if isinstance(f, dict) else f
                    age  = f.get("created", "")[:10] if isinstance(f, dict) else ""
                    ep_lines.append(f"  - {text[:CONTEXT_FACT_CHARS]}" + (f" ({age})" if age else ""))

            if self.data["sessions"]:
                ep_lines.append("\nÚltimas tarefas executadas:")
                for s in self.data["sessions"][-5:]:
                    ep_lines.append(f"  [{s['timestamp'][:10]}] {s['task'][:80]}")
                    ep_lines.append(f"    Resultado: {s['result'][:100]}")

        ep_lines.append("=========================\n")
        lines.append("\n".join(ep_lines))

        return "\n".join(lines)
