import json
import logging
import os
from datetime import datetime

log = logging.getLogger(__name__)

PROFILE_FILE = os.path.join(os.path.dirname(__file__), "workspace", "user_profile.json")

TECH_LEVELS = ["iniciante", "intermediário", "avançado", "especialista"]
TONES       = ["informal", "neutro", "formal", "técnico"]

DEFAULT_PROFILE = {
    "name":            "",
    "tech_level":      "intermediário",
    "tone":            "neutro",
    "language":        "pt-BR",
    "preferences":     [],
    "topics_interest": [],
    "study_progress":  {},
    "interactions":    0,
    "created":         "",
    "updated":         "",
}

_LEVEL_INSTRUCTIONS = {
    "iniciante":     "Use linguagem simples. Evite jargões. Explique passo a passo com analogias do cotidiano.",
    "intermediário": "Balance clareza com profundidade técnica. Use exemplos práticos.",
    "avançado":      "Seja direto e técnico. Use terminologia especializada sem explicar o básico.",
    "especialista":  "Máxima profundidade técnica. Discuta trade-offs, edge cases e nuances avançadas.",
}

_TONE_INSTRUCTIONS = {
    "informal": "Tom descontraído. Pode usar humor moderado.",
    "neutro":   "Tom profissional mas acessível.",
    "formal":   "Tom formal e preciso.",
    "técnico":  "Foco em precisão técnica e terminologia exata.",
}


class UserProfile:
    def __init__(self):
        self.data = self._load()

    def _load(self) -> dict:
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                return {**DEFAULT_PROFILE, **saved}
            except Exception:
                pass
        profile = {**DEFAULT_PROFILE, "created": datetime.now().isoformat()}
        self._write(profile)
        return profile

    def _write(self, data: dict):
        os.makedirs(os.path.dirname(PROFILE_FILE), exist_ok=True)
        data["updated"] = datetime.now().isoformat()
        try:
            with open(PROFILE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.warning("UserProfile._write: %s", e)

    def save(self):
        self._write(self.data)

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if k in DEFAULT_PROFILE:
                self.data[k] = v
        self.save()
        log.info("UserProfile atualizado: %s", list(kwargs.keys()))

    def increment_interactions(self):
        self.data["interactions"] = self.data.get("interactions", 0) + 1
        self.save()

    def add_preference(self, pref: str):
        prefs = self.data.get("preferences", [])
        if pref not in prefs:
            prefs.append(pref)
            self.data["preferences"] = prefs[-20:]
            self.save()

    def add_interest(self, topic: str):
        topics = self.data.get("topics_interest", [])
        if topic not in topics:
            topics.append(topic)
            self.data["topics_interest"] = topics[-15:]
            self.save()

    def update_study_progress(self, subject: str, level: int):
        """Rastreia progresso de estudo por assunto (0-100)."""
        self.data.setdefault("study_progress", {})[subject] = level
        self.save()

    def get_system_context(self) -> str:
        lines = ["=== PERFIL DO USUÁRIO ==="]
        if self.data.get("name"):
            lines.append(f"Nome: {self.data['name']}")
        level = self.data.get("tech_level", "intermediário")
        tone  = self.data.get("tone", "neutro")
        lines.append(f"Nível técnico: {level}")
        lines.append(f"Tom preferido: {tone}")
        prefs = self.data.get("preferences", [])
        if prefs:
            lines.append(f"Preferências: {', '.join(prefs[:5])}")
        interests = self.data.get("topics_interest", [])
        if interests:
            lines.append(f"Interesses: {', '.join(interests[:5])}")
        progress = self.data.get("study_progress", {})
        if progress:
            prog_str = ", ".join(f"{k}:{v}%" for k, v in list(progress.items())[:5])
            lines.append(f"Progresso de estudo: {prog_str}")
        lines.append("========================")
        lines.append(f"COMUNICAÇÃO: {_LEVEL_INSTRUCTIONS.get(level, '')}")
        lines.append(f"TOM: {_TONE_INSTRUCTIONS.get(tone, '')}")
        lines.append("")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return dict(self.data)
