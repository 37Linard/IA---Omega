import os
import re
from datetime import datetime

OBSIDIAN_DIR = r"C:\Users\User\Documents\Obsidian Vault\Gabriel\Agente IA"


class SaveNoteTool:
    name = "save_note"
    description = (
        "Salva uma nota no Obsidian (pasta Gabriel/Agente IA). "
        "Input: {'title': 'Título da nota', 'content': 'Conteúdo em markdown'}"
    )

    def run(self, input_data: dict) -> str:
        title   = input_data.get("title", "").strip()
        content = input_data.get("content", "").strip()

        if not title:
            return "Erro: campo 'title' obrigatório."
        if not content:
            return "Erro: campo 'content' obrigatório."

        # Sanitiza nome do arquivo
        safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
        safe_title = safe_title.strip()[:80]

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_prefix} — {safe_title}.md"
        filepath = os.path.join(OBSIDIAN_DIR, filename)

        # Monta nota com frontmatter Obsidian
        note = f"""---
criado: {timestamp}
tags: [agente-ia]
---

# {title}

{content}
"""

        try:
            os.makedirs(OBSIDIAN_DIR, exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(note)
            return f"Nota salva no Obsidian: Gabriel/Agente IA/{filename}"
        except Exception as e:
            return f"Erro ao salvar nota: {str(e)}"
