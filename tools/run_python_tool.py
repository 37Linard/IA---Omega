import subprocess
import tempfile
import os


BLOCKED = [
    "os.remove", "os.rmdir", "shutil.rmtree", "shutil.rmdir",
    "open(", "subprocess", "__import__", "eval(", "exec(",
    "os.system", "os.popen", "importlib",
]


class RunPythonTool:
    name = "run_python"
    description = (
        "Escreve e executa código Python. Retorna stdout e stderr. "
        "Input: {'code': 'print(1+1)'}"
    )

    def run(self, input_data: dict) -> str:
        code = input_data.get("code", "")

        if not code.strip():
            return "Erro: campo 'code' obrigatório."

        # Bloqueia operações destrutivas
        for pattern in BLOCKED:
            if pattern in code:
                return f"Bloqueado: '{pattern}' não permitido por segurança."

        # Escreve código em arquivo temporário
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            delete=False,
            encoding="utf-8"
        ) as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            result = subprocess.run(
                ["python", tmp_path],
                capture_output=True,
                text=True,
                timeout=10,           # mata após 10 segundos
                cwd=tempfile.gettempdir()
            )

            output = ""

            if result.stdout.strip():
                output += f"STDOUT:\n{result.stdout.strip()}"

            if result.stderr.strip():
                output += f"\nSTDERR:\n{result.stderr.strip()}"

            if not output:
                output = "Código executado sem saída."

            return output

        except subprocess.TimeoutExpired:
            return "Erro: execução excedeu 10 segundos e foi encerrada."
        except Exception as e:
            return f"Erro ao executar código: {str(e)}"
        finally:
            os.unlink(tmp_path)
