"""
Fine-tuning da Nova com Unsloth + QLoRA.

Roda em WSL2 ou Linux. Na RTX 2060 (6GB VRAM):
- qwen2.5:7b em 4-bit: ~4.5GB VRAM para treino
- Tempo estimado: 2-4h para ~500 exemplos

Setup:
    pip install unsloth
    pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

Uso:
    python train.py
    python train.py --model qwen2.5:7b --epochs 3 --output ./nova-model
"""

import argparse
import json
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model",   default="Qwen/Qwen2.5-7B-Instruct", help="Modelo base HuggingFace")
    p.add_argument("--dataset", default="./dataset.jsonl")
    p.add_argument("--output",  default="./nova-lora")
    p.add_argument("--epochs",  type=int, default=3)
    p.add_argument("--batch",   type=int, default=2)
    p.add_argument("--lr",      type=float, default=2e-4)
    p.add_argument("--max_len", type=int, default=2048)
    return p.parse_args()


def load_dataset(path: str):
    data = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                data.append(json.loads(line))
            except Exception:
                pass
    return data


def sharegpt_to_text(sample: dict, tokenizer) -> str:
    """Converte formato ShareGPT para texto de treino usando o chat template."""
    convs = sample.get("conversations", [])
    messages = []
    for c in convs:
        role = c.get("from", "")
        content = c.get("value", "")
        if role == "system":
            messages.append({"role": "system", "content": content})
        elif role == "human":
            messages.append({"role": "user", "content": content})
        elif role == "assistant":
            messages.append({"role": "assistant", "content": content})
    if not messages:
        return ""
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)


def main():
    args = parse_args()

    print("=== Fine-tuning Nova ===")
    print(f"Modelo base:  {args.model}")
    print(f"Dataset:      {args.dataset}")
    print(f"Output:       {args.output}")
    print(f"Epochs:       {args.epochs}")
    print()

    # ── Imports Unsloth ──────────────────────────────────────────────────────
    try:
        from unsloth import FastLanguageModel
        import torch
    except ImportError:
        print("ERRO: Unsloth não instalado.")
        print("  pip install unsloth")
        print("  pip install torch --index-url https://download.pytorch.org/whl/cu121")
        return

    # ── Carrega modelo com Unsloth (4-bit QLoRA) ─────────────────────────────
    print("Carregando modelo base...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name     = args.model,
        max_seq_length = args.max_len,
        dtype          = None,       # auto-detect (bfloat16 se disponível)
        load_in_4bit   = True,       # QLoRA 4-bit — cabe em 6GB VRAM
    )

    # ── Aplica LoRA ──────────────────────────────────────────────────────────
    print("Aplicando LoRA...")
    model = FastLanguageModel.get_peft_model(
        model,
        r              = 16,         # rank LoRA — 16 é bom equilíbrio
        target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                          "gate_proj", "up_proj", "down_proj"],
        lora_alpha     = 16,
        lora_dropout   = 0,
        bias           = "none",
        use_gradient_checkpointing = "unsloth",
        random_state   = 42,
    )

    # ── Carrega e prepara dataset ─────────────────────────────────────────────
    print(f"Carregando dataset: {args.dataset}")
    raw_data = load_dataset(args.dataset)
    print(f"  {len(raw_data)} exemplos carregados")

    texts = []
    for sample in raw_data:
        text = sharegpt_to_text(sample, tokenizer)
        if text and len(text) > 50:
            texts.append({"text": text})

    print(f"  {len(texts)} exemplos válidos após processamento")

    from datasets import Dataset
    dataset = Dataset.from_list(texts)

    # ── Tokenização ──────────────────────────────────────────────────────────
    def tokenize(examples):
        return tokenizer(
            examples["text"],
            truncation      = True,
            max_length      = args.max_len,
            padding         = False,
        )

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])

    # ── Trainer ──────────────────────────────────────────────────────────────
    from transformers import TrainingArguments, DataCollatorForSeq2Seq
    from trl import SFTTrainer

    trainer = SFTTrainer(
        model         = model,
        tokenizer     = tokenizer,
        train_dataset = tokenized,
        dataset_text_field = "input_ids",
        max_seq_length     = args.max_len,
        data_collator      = DataCollatorForSeq2Seq(tokenizer, pad_to_multiple_of=8),
        args = TrainingArguments(
            output_dir              = args.output,
            num_train_epochs        = args.epochs,
            per_device_train_batch_size = args.batch,
            gradient_accumulation_steps = 4,
            warmup_steps            = 10,
            learning_rate           = args.lr,
            fp16                    = not torch.cuda.is_bf16_supported(),
            bf16                    = torch.cuda.is_bf16_supported(),
            logging_steps           = 10,
            save_steps              = 100,
            save_total_limit        = 2,
            optim                   = "adamw_8bit",
            weight_decay            = 0.01,
            lr_scheduler_type       = "cosine",
            report_to               = "none",
        ),
    )

    # ── Treino ───────────────────────────────────────────────────────────────
    print("\nIniciando treino...")
    print(f"  VRAM disponível: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    trainer_stats = trainer.train()

    print(f"\n✓ Treino concluído em {trainer_stats.metrics['train_runtime']:.0f}s")
    print(f"  Loss final: {trainer_stats.metrics['train_loss']:.4f}")

    # ── Salva modelo ─────────────────────────────────────────────────────────
    print(f"\nSalvando LoRA adapter em {args.output}...")
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print("✓ LoRA adapter salvo")

    # ── Exporta GGUF ─────────────────────────────────────────────────────────
    print("\nExportando para GGUF (Q4_K_M)...")
    gguf_path = Path(args.output) / "nova.gguf"
    model.save_pretrained_gguf(
        str(gguf_path.parent / "nova"),
        tokenizer,
        quantization_method = "q4_k_m",  # boa qualidade, 4GB aprox
    )
    print(f"✓ GGUF salvo: {gguf_path.parent / 'nova-unsloth.Q4_K_M.gguf'}")
    print("\nPróximo passo: python export_ollama.py")


if __name__ == "__main__":
    main()
