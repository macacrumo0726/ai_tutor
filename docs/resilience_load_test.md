# Resiliencia y prueba de carga

## Cambios implementados

- Las generaciones se serializan parcialmente con un semáforo configurable:
  `AI_TUTOR_MAX_CONCURRENT_GENERATIONS` (por defecto `2`). Las solicitudes
  adicionales esperan en una cola breve.
- Si una solicitud espera más de `AI_TUTOR_QUEUE_TIMEOUT_SECONDS` (por defecto
  `12` s), recibe una respuesta local determinista y se guarda como
  `instructional_emergency`; no se muestra un error técnico.
- El cliente Ollama no reintenta internamente (`LOCAL_LLM_MAX_RETRIES=0`), para
  que el fallback del API sea predecible y no multiplique la latencia.
- Si todos los proveedores devuelven timeout, `429`, `503`, salida vacía,
  idioma incorrecto o tema irrelevante, el servicio conserva el turno y usa el
  mismo fallback local de emergencia.
- Los errores técnicos permanecen en metadata/logs para investigación, pero no
  llegan al estudiante.

## Ejecución

```bash
.venv/bin/python scripts/load_test_chat.py
```

El script crea usuarios y conversaciones aisladas, acepta el protocolo vigente
y ejecuta una pregunta por usuario con concurrencia `1, 3, 5 y 10`. El informe
se guarda en `data/evaluation/load_test_chat.json`.

## Resultado ejecutado

| Concurrencia | Éxitos | Fallbacks | p50 | p95 | Errores visibles |
|---:|---:|---:|---:|---:|---:|
| 1 | 1/1 | 0 | 19,6 s | 19,6 s | 0 |
| 3 | 3/3 | 1 | 21,7 s | 21,7 s | 0 |
| 5 | 5/5 | 3 | 12,6 s | 22,0 s | 0 |
| 10 | 10/10 | 8 | 12,9 s | 22,1 s | 0 |

La máquina local no puede generar diez respuestas Qwen simultáneamente con la
misma latencia, pero ninguna solicitud terminó en error HTTP ni dejó al
estudiante esperando indefinidamente. Bajo saturación, el fallback de emergencia
es el mecanismo que garantiza disponibilidad. Para un piloto real conviene
medir también la calidad de esas respuestas y guardar el porcentaje de turnos
que utilizó fallback.
