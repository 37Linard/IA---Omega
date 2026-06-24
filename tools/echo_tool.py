class EchoTool:
    name = "echo"
    description = "Repete o texto fornecido. Input: {'text': 'seu texto'}"

    def run(self, input_data):
        if isinstance(input_data, dict):
            return input_data.get("text", "sem texto")
        return str(input_data)
