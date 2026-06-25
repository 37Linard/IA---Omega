from memory import Memory


class RememberFactTool:
    name = "remember_fact"
    description = (
        "Salva um fato importante na memória persistente do agente para uso futuro. "
        "Use quando descobrir informação relevante e duradoura (preferências, dados fixos, configurações). "
        "Input: {'fact': 'texto do fato a lembrar'}"
    )

    def __init__(self):
        self.memory = None  # injetado pelo api.py após criação do agente

    def run(self, input_data: dict) -> str:
        fact = input_data.get("fact", "").strip()
        if not fact:
            return "Erro: campo 'fact' obrigatório."
        if self.memory is None:
            self.memory = Memory()
        self.memory.save_fact(fact)
        return f"Fato memorizado: {fact}"
