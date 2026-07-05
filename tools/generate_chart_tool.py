import os
import logging

log = logging.getLogger(__name__)

CHART_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace", "charts")

CHART_TYPES = {"bar", "line", "pie", "scatter", "area", "horizontal_bar"}


class GenerateChartTool:
    name = "generate_chart"
    description = (
        "Gera gráficos (barras, linhas, pizza, dispersão). "
        "Input: {'type': 'bar|line|pie|scatter|area|horizontal_bar', "
        "'labels': ['Jan','Fev'], 'values': [100, 150], "
        "'title': 'Título', 'xlabel': 'Eixo X', 'ylabel': 'Eixo Y', "
        "'output': 'grafico.png'}"
    )

    def run(self, input_data: dict) -> str:
        chart_type = input_data.get("type", "bar").lower()
        labels     = input_data.get("labels", [])
        values     = input_data.get("values", [])
        title      = input_data.get("title", "Gráfico")
        xlabel     = input_data.get("xlabel", "")
        ylabel     = input_data.get("ylabel", "")
        output     = input_data.get("output", "chart.png")

        if chart_type not in CHART_TYPES:
            return f"Tipo inválido: '{chart_type}'. Use: {', '.join(sorted(CHART_TYPES))}"
        if not values:
            return "Erro: 'values' obrigatório."
        if chart_type != "pie" and len(labels) != len(values):
            labels = [str(i + 1) for i in range(len(values))]

        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            return "Dependência ausente: matplotlib. Execute: pip install matplotlib"

        try:
            os.makedirs(CHART_DIR, exist_ok=True)
            safe_output = os.path.basename(output)
            if not safe_output.endswith(".png"):
                safe_output += ".png"
            filepath = os.path.join(CHART_DIR, safe_output)

            # Tema dark igual ao chat (--chat-bg #212121, --accent #6366f1) —
            # evita caixa branca destoando no meio da conversa escura
            BG, FG, GRID, ACCENT = "#212121", "#e5e5e5", "#333333", "#6366f1"
            PIE_COLORS = ["#6366f1", "#818cf8", "#a5b4fc", "#4f46e5", "#c7d2fe", "#312e81"]

            plt.style.use("dark_background")
            fig, ax = plt.subplots(figsize=(10, 6))
            fig.patch.set_facecolor(BG)
            ax.set_facecolor(BG)

            if chart_type == "bar":
                ax.bar(labels, values, color=ACCENT, edgecolor=BG)
            elif chart_type == "horizontal_bar":
                ax.barh(labels, values, color=ACCENT, edgecolor=BG)
            elif chart_type == "line":
                ax.plot(labels, values, marker="o", color=ACCENT, linewidth=2)
                ax.fill_between(range(len(labels)), values, alpha=0.15, color=ACCENT)
            elif chart_type == "area":
                ax.fill_between(range(len(labels)), values, alpha=0.4, color=ACCENT)
                ax.plot(range(len(labels)), values, color=ACCENT, linewidth=2)
                ax.set_xticks(range(len(labels)))
                ax.set_xticklabels(labels)
            elif chart_type == "pie":
                colors = [PIE_COLORS[i % len(PIE_COLORS)] for i in range(len(values))]
                ax.pie(values, labels=labels or None, autopct="%1.1f%%", startangle=90,
                       colors=colors, textprops={"color": FG})
            elif chart_type == "scatter":
                if len(values) > 0 and isinstance(values[0], (list, tuple)):
                    x_vals = [v[0] for v in values]
                    y_vals = [v[1] for v in values]
                else:
                    x_vals = list(range(len(values)))
                    y_vals = values
                ax.scatter(x_vals, y_vals, color=ACCENT, alpha=0.85)

            ax.set_title(title, fontsize=14, fontweight="bold", pad=15, color=FG)
            ax.tick_params(colors=FG)
            for spine in ax.spines.values():
                spine.set_color(GRID)
            ax.grid(axis="y", color=GRID, linewidth=0.6)
            if xlabel:
                ax.set_xlabel(xlabel, color=FG)
            if ylabel:
                ax.set_ylabel(ylabel, color=FG)

            plt.tight_layout()
            plt.savefig(filepath, dpi=150, bbox_inches="tight", facecolor=BG)
            plt.close(fig)

            log.info("Gráfico salvo: %s", filepath)

            try:
                from tools.browser_tool import _img_url
                url = _img_url(f"charts/{safe_output}")
            except Exception:
                from config import API_URL
                url = f"{API_URL}/workspace/img/charts/{safe_output}"

            return f"Gráfico '{title}' salvo em: {filepath}\n![{title}]({url})"
        except Exception as e:
            return f"Erro ao gerar gráfico: {str(e)}"
