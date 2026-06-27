import os
from datetime import datetime

_WORKSPACE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")


class GenerateReportTool:
    name = "generate_report"
    description = (
        "Gera relatório estruturado em Markdown com seções padronizadas e salva em arquivo. "
        "Input: {'title': 'Título', 'summary': 'resumo executivo', "
        "'data': 'dados brutos', 'analysis': 'análise técnica', "
        "'alerts': 'alertas/riscos (opcional)', 'sources': 'fontes (opcional)', "
        "'filename': 'nome_arquivo.md (opcional)'}"
    )

    def run(self, params: dict) -> str:
        title    = params.get("title", "Relatório")
        summary  = params.get("summary", "")
        data     = params.get("data", "")
        analysis = params.get("analysis", "")
        alerts   = params.get("alerts", "")
        sources  = params.get("sources", "")
        filename = params.get("filename", f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.md")

        filename = os.path.basename(filename)
        if not filename.endswith(".md"):
            filename += ".md"

        now = datetime.now()

        sections = [
            f"# {title}",
            f"> Gerado em {now.strftime('%d/%m/%Y às %H:%M')}",
            "",
            "---",
            "",
            "## Resumo Executivo",
            summary or "_Sem resumo._",
            "",
        ]

        if data:
            sections += ["## Dados", data, ""]

        if analysis:
            sections += ["## Análise Técnica", analysis, ""]

        if alerts:
            sections += ["## ⚠️ Alertas e Riscos", alerts, ""]

        if sources:
            sections += ["## Fontes", sources, ""]

        sections += [
            "---",
            "_Relatório gerado automaticamente por Agente IA Local_",
        ]

        content = "\n".join(sections)

        os.makedirs(_WORKSPACE, exist_ok=True)
        path = os.path.join(_WORKSPACE, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Relatório salvo: {path}\n\nPreview:\n{content[:600]}{'...' if len(content) > 600 else ''}"
