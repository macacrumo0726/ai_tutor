# Matriz experimental con modelos open-source

## Principio

El modelo generador y el acceso a conocimiento son variables independientes.
No debe llamarse “RAG” a un cambio de modelo ni atribuir al fine-tuning una
mejora causada por contexto recuperado.

La UI implementa cuatro selectores independientes: familia, adaptación,
condición instruccional y recuperación. Las combinaciones técnicamente
imposibles se rechazan de forma explícita.

| Modelo | Conocimiento | Condición |
|---|---|---|
| Base open-source | Ninguno | LLM normal |
| Base open-source | RAG instruccional | Efecto de recuperación documental |
| Base open-source | Graph-RAG | Efecto de estructura explícita |
| Base open-source | PEP-SA-RAG | Efecto de prerrequisitos + dinámica |
| Fine-tuned, mismo modelo base | Ninguno | Efecto aislado del SFT pedagógico |
| Fine-tuned, mismo modelo base | RAG instruccional | SFT + evidencia documental |
| Fine-tuned, mismo modelo base | Graph-RAG | SFT + estructura |
| Fine-tuned, mismo modelo base | PEP-SA-RAG | Sistema completo |

Todas las condiciones deben fijar temperatura, semilla, límite de tokens y
plantilla de chat. Para aislar el efecto de la base, comparar primero las cuatro
filas del mismo modelo. Para aislar SFT, comparar verticalmente cada pareja con
igual conocimiento.

## Modelo recomendado

Primera opción: `Qwen/Qwen3-8B`, por capacidad multilingüe/matemática, licencia
Apache 2.0, tamaño entrenable mediante QLoRA y soporte en Transformers/vLLM.
Para pruebas con menos memoria puede usarse una variante Qwen3 menor, pero no
debe mezclarse el tamaño del modelo dentro de una comparación.

Llama 3.1 8B Instruct es una alternativa, pero requiere aceptar su licencia y
acceso en Hugging Face. La comparación principal debería usar una sola familia.

Además se incluye `DeepSeek-R1-Distill-Qwen-7B` como segunda familia local
entrenable. No se equipara con el endpoint comercial DeepSeek API.

## Fine-tuning

El objetivo del SFT es enseñar **comportamiento pedagógico**, no memorizar el
libro. Los targets deben exhibir diagnóstico, activación previa, scaffolding,
micro-checks y consolidación. La evidencia factual continúa en RAG.

Pipeline:

```bash
python scripts/build_sft_dataset.py
pip install -e '.[training]'
python scripts/finetune_qlora.py \
  --model Qwen/Qwen3-8B \
  --dataset data/training/precalculus_sft.jsonl
```

El entrenamiento QLoRA debe ejecutarse en Linux/CUDA. Los splits validation y
test no se usan para actualizar pesos. Antes de un entrenamiento doctoral, las
respuestas objetivo generadas deben someterse a revisión matemática y
pedagógica; la versión actual sirve para validar el pipeline, no como gold final.

## Inferencia local

La aplicación usa un endpoint OpenAI-compatible. Puede conectarse a Ollama,
vLLM, SGLang o LM Studio mediante:

```text
LOCAL_LLM_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_BASE_MODEL=qwen3:8b
LOCAL_FINETUNED_MODEL=precalculus-tutor-qwen3:8b
```

El mismo servidor debe alojar el modelo base y la versión fine-tuned. Para una
comparación controlada no se debe cambiar cuantización, sampling ni plantilla.
