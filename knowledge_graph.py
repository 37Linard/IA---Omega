"""
Knowledge Graph — extrai e armazena entidades + relações da conversa.
Persiste em workspace/knowledge_graph.json.
Extração acontece em background (não bloqueia resposta).
"""
import json
import logging
import os
import re
import threading

log = logging.getLogger(__name__)

GRAPH_FILE = os.path.join(os.path.dirname(__file__), "workspace", "knowledge_graph.json")
MAX_ENTITIES  = 500
MAX_RELATIONS = 2000


class KnowledgeGraph:
    def __init__(self):
        self._lock  = threading.Lock()
        self._graph = self._load()

    def _load(self) -> dict:
        if os.path.exists(GRAPH_FILE):
            try:
                with open(GRAPH_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"entities": {}, "relations": []}

    def _save(self):
        os.makedirs(os.path.dirname(GRAPH_FILE), exist_ok=True)
        with open(GRAPH_FILE, "w", encoding="utf-8") as f:
            json.dump(self._graph, f, indent=2, ensure_ascii=False)

    def add_triple(self, subject: str, predicate: str, obj: str):
        subject   = subject.strip()[:80]
        predicate = predicate.strip()[:40]
        obj       = obj.strip()[:80]
        if not all([subject, predicate, obj]):
            return

        with self._lock:
            for e in [subject, obj]:
                if e not in self._graph["entities"]:
                    self._graph["entities"][e] = {"count": 0}
                self._graph["entities"][e]["count"] += 1

            for rel in self._graph["relations"]:
                if rel["s"] == subject and rel["p"] == predicate and rel["o"] == obj:
                    rel["count"] += 1
                    self._save()
                    return

            self._graph["relations"].append({"s": subject, "p": predicate, "o": obj, "count": 1})

            # Prune se muito grande
            if len(self._graph["relations"]) > MAX_RELATIONS:
                self._graph["relations"].sort(key=lambda r: r["count"], reverse=True)
                self._graph["relations"] = self._graph["relations"][:MAX_RELATIONS]
            if len(self._graph["entities"]) > MAX_ENTITIES:
                top = sorted(self._graph["entities"].items(), key=lambda x: x[1]["count"], reverse=True)
                self._graph["entities"] = dict(top[:MAX_ENTITIES])

            self._save()

    def add_triples(self, triples: list[dict]):
        for t in triples:
            s = t.get("s") or t.get("sujeito") or t.get("subject", "")
            p = t.get("p") or t.get("relação") or t.get("relacao") or t.get("predicate", "")
            o = t.get("o") or t.get("objeto") or t.get("object", "")
            if s and p and o:
                self.add_triple(s, p, o)

    def query(self, topic: str, max_results: int = 15) -> list[str]:
        """Retorna fatos relacionados ao tópico (busca parcial, case-insensitive)."""
        topic_l = topic.lower()
        found   = []

        with self._lock:
            matched_entities = [e for e in self._graph["entities"] if topic_l in e.lower()]
            for m in matched_entities:
                for rel in self._graph["relations"]:
                    if rel["s"] == m:
                        found.append((rel["count"], f"{m} -[{rel['p']}]-> {rel['o']}"))
                    elif rel["o"] == m:
                        found.append((rel["count"], f"{rel['s']} -[{rel['p']}]-> {m}"))

        found.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in found[:max_results]]

    def get_context(self, topic: str) -> str:
        if not topic:
            return ""
        facts = self.query(topic.split()[0] if topic else "")
        if not facts:
            return ""
        lines = ["=== GRAFO DE CONHECIMENTO ==="]
        lines.extend(f"  - {f}" for f in facts[:8])
        lines.append("=============================\n")
        return "\n".join(lines)

    def extract_async(self, text: str, llm) -> None:
        """Extrai entidades/relações do texto em background."""
        t = threading.Thread(target=self._extract, args=(text, llm), daemon=True)
        t.start()

    def _extract(self, text: str, llm) -> None:
        prompt = (
            "Extraia entidades e relações do texto abaixo. "
            "Responda APENAS em JSON válido (sem texto adicional):\n"
            '[{"s": "entidade1", "p": "relação", "o": "entidade2"}]\n\n'
            f"Texto: {text[:600]}\n\nJSON:"
        )
        try:
            raw   = llm.generate(prompt)
            start = raw.find("[")
            end   = raw.rfind("]") + 1
            if start >= 0 and end > start:
                triples = json.loads(raw[start:end])
                if isinstance(triples, list):
                    self.add_triples(triples)
                    log.debug("KnowledgeGraph: %d triplas extraídas", len(triples))
        except Exception as e:
            log.debug("KnowledgeGraph._extract: %s", e)

    def stats(self) -> dict:
        with self._lock:
            return {
                "entities": len(self._graph["entities"]),
                "relations": len(self._graph["relations"]),
            }
