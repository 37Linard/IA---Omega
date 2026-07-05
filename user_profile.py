import json
import logging
import os
import re
from datetime import datetime

log = logging.getLogger(__name__)

PROFILE_FILE = os.path.join(os.path.dirname(__file__), "workspace", "user_profile.json")

TECH_LEVELS = ["iniciante", "intermediário", "avançado", "especialista"]
TONES       = ["informal", "neutro", "formal", "técnico"]

DEFAULT_PROFILE = {
    "name":              "",
    "tech_level":        "intermediário",
    "tech_level_auto":   True,   # False assim que o usuário seta tech_level manualmente
    "tech_score":        0.0,    # EMA do sinal técnico das mensagens — não exposto na UI
    "tech_observations": 0,      # mensagens observadas — evita ajustar nível cedo demais
    "tone":              "neutro",
    "language":          "pt-BR",
    "preferences":       [],
    "topics_interest":   [],
    "study_progress":    {},
    "interactions":      0,
    "created":           "",
    "updated":           "",
}

# ── Auto-detecção de nível técnico ──────────────────────────────────────────
# Heurística leve (sem chamada de LLM), mesmo espírito do domain_hits() em
# orchestrator.py: conta jargão técnico e sinais de "sou iniciante" na
# mensagem em vez de pedir pro modelo classificar (custaria uma inferência
# extra por turno).
_ADVANCED_TERMS = {
    "algoritmo", "algoritmos", "complexidade", "kubernetes", "docker", "endpoint",
    "endpoints", "assincrono", "assíncrono", "threading", "regex", "índice", "indice",
    "query", "queries", "framework", "dependencia", "dependência", "compilar",
    "runtime", "stacktrace", "stack trace", "exception", "debugar", "refatorar",
    "refatoracao", "refatoração", "arquitetura", "middleware", "cache", "concorrencia",
    "concorrência", "mutex", "websocket", "kubectl", "microservico", "microserviço",
    "orm", "schema", "migracao", "migração", "deploy", "ci/cd", "sdk",
    "backend", "frontend", "async", "await", "callback", "closure", "recursao",
    "recursão", "buffer", "socket", "protocolo", "criptografia", "hash", "jwt",
    "oauth", "webhook", "orquestracao", "orquestração", "pipeline", "container",
    "namespace", "singleton", "polimorfismo", "heranca", "herança", "big o",
}

_BEGINNER_PHRASES = (
    "não entendi", "nao entendi", "o que é", "o que e", "pra que serve",
    "para que serve", "como assim", "sou iniciante", "nunca programei",
    "explica simples", "explica mais simples", "não sei nada de",
    "nao sei nada de", "sou leigo", "sou leiga", "primeira vez que",
    "estou aprendendo", "iniciando agora", "explica como se eu",
    "não manjo", "nao manjo", "sou novo nisso", "sou novato", "sou novata",
)

_CODE_PATTERN = re.compile(r'```|`[^`\n]{3,}`|\bdef \w+\(|\bfunction\s*\(|\bimport \w+|\bclass \w+|SELECT .+ FROM|=>')

_SCORE_THRESHOLDS = (
    (1.2, "especialista"),
    (0.4, "avançado"),
    (-0.4, "intermediário"),
)


def _detect_tech_signal(text: str) -> float:
    t = text.lower()
    signal = 0.0

    advanced_hits = sum(1 for term in _ADVANCED_TERMS if term in t)
    signal += min(advanced_hits, 3) * 0.5

    if _CODE_PATTERN.search(text):
        signal += 0.8

    beginner_hits = sum(1 for phrase in _BEGINNER_PHRASES if phrase in t)
    signal -= min(beginner_hits, 2) * 1.0

    return max(-2.0, min(2.0, signal))


def _level_from_score(score: float) -> str:
    for threshold, level in _SCORE_THRESHOLDS:
        if score >= threshold:
            return level
    return "iniciante"

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

    def observe_message(self, text: str):
        """Atualiza o nível técnico estimado a partir do texto da mensagem.
        Não faz nada se o usuário já travou o nível manualmente (tech_level_auto=False)
        via POST /profile — auto-detecção nunca sobrescreve escolha explícita."""
        if not text or not self.data.get("tech_level_auto", True):
            return

        signal = _detect_tech_signal(text)
        prev_score = self.data.get("tech_score", 0.0)
        score = prev_score * 0.8 + signal * 0.2
        self.data["tech_score"] = round(score, 3)
        self.data["tech_observations"] = self.data.get("tech_observations", 0) + 1

        # espera algumas mensagens antes de ajustar — evita virar o nível na
        # primeira frase técnica ou confusa que aparecer
        if self.data["tech_observations"] < 3:
            self.save()
            return

        new_level = _level_from_score(score)
        if new_level != self.data.get("tech_level"):
            self.data["tech_level"] = new_level
            log.info("UserProfile: nível técnico auto-detectado -> %s (score=%.2f)", new_level, score)
        self.save()

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
        auto_tag = " (auto-detectado)" if self.data.get("tech_level_auto", True) else ""
        lines.append(f"Nível técnico: {level}{auto_tag}")
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
