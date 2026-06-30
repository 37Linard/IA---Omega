"""
Registra a Nova no Ollama após o treino.
Roda no Windows depois do treino no WSL2.

Uso:
    python export_ollama.py --gguf ./nova-lora/nova-unsloth.Q4_K_M.gguf
    python export_ollama.py --gguf ./nova-lora/nova-unsloth.Q4_K_M.gguf --name nova:latest
"""

import argparse
import subprocess
import sys
from pathlib import Path

MODELFILE_TEMPLATE = '''FROM {gguf_path}

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096

SYSTEM """
{system_prompt}
"""
'''

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gguf",   required=True, help="Caminho para o arquivo .gguf")
    p.add_argument("--name",   default="nova:latest", help="Nome do modelo no Ollama")
    p.add_argument("--system", default=None, help="System prompt customizado (opcional)")
    args = p.parse_args()

    gguf = Path(args.gguf).resolve()
    if not gguf.exists():
        print(f"ERRO: arquivo não encontrado: {gguf}")
        sys.exit(1)

    if args.system:
        system_prompt = args.system
    else:
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from persona import SYSTEM_PROMPT
            system_prompt = SYSTEM_PROMPT
        except ImportError:
            system_prompt = "Você é Nova, uma IA assistente versátil e com personalidade marcante."

    modelfile_content = MODELFILE_TEMPLATE.format(
        gguf_path     = str(gguf).replace("\\", "/"),
        system_prompt = system_prompt.strip(),
    )

    modelfile_path = gguf.parent / "Modelfile"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"✓ Modelfile criado: {modelfile_path}")

    print(f"\nRegistrando '{args.name}' no Ollama...")
    result = subprocess.run(
        ["ollama", "create", args.name, "-f", str(modelfile_path)],
        capture_output=True, text=True, encoding="utf-8"
    )

    if result.returncode == 0:
        print(f"✓ Modelo '{args.name}' registrado no Ollama")
        print("\nTestar:")
        print(f"  ollama run {args.name}")
        print("\nAtualizar sistema:")
        print(f"  Edite config.py → MODEL = '{args.name}'")
    else:
        print(f"ERRO ao registrar: {result.stderr}")
        print("Tente manualmente:")
        print(f"  ollama create {args.name} -f {modelfile_path}")


if __name__ == "__main__":
    main()
