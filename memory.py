import json
import os
from datetime import datetime

MEMORY_FILE = r"C:\Users\User\Desktop\MEU\IA\agent_memory.json"


class Memory:
    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"sessions": [], "facts": []}

    def _save(self):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def save_session(self, task: str, result: str, scratchpad: list):
        session = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "steps": len(scratchpad)
        }
        self.data["sessions"].append(session)
        # Mantém apenas últimas 20 sessões
        self.data["sessions"] = self.data["sessions"][-20:]
        self._save()

    def save_fact(self, fact: str):
        if fact not in self.data["facts"]:
            self.data["facts"].append(fact)
            self._save()

    def get_context(self) -> str:
        if not self.data["sessions"] and not self.data["facts"]:
            return ""

        lines = ["=== MEMÓRIA DO AGENTE ==="]

        if self.data["facts"]:
            lines.append("\nFatos importantes:")
            for f in self.data["facts"]:
                lines.append(f"  - {f}")

        if self.data["sessions"]:
            lines.append("\nÚltimas tarefas executadas:")
            for s in self.data["sessions"][-5:]:
                lines.append(f"  [{s['timestamp'][:10]}] {s['task'][:80]}")
                lines.append(f"    Resultado: {s['result'][:100]}")

        lines.append("=========================\n")
        return "\n".join(lines)
