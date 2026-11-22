# Validación de conversaciones informada por ejercicios abiertos

Fecha de ejecución: 2026-11-05. Esta prueba usa diálogos sintéticos; no se
copian conversaciones de estudiantes. Los casos se diseñaron a partir de
errores y procedimientos que aparecen en recursos educativos abiertos:

- OpenStax define el dominio como los valores de entrada permitidos y pide
  excluir división por cero y raíces pares de números negativos
  ([Domain and Range](https://openstax.org/books/precalculus/pages/1-2-domain-and-range)).
- OpenStax recuerda que una función asigna una única salida a cada entrada
  ([Functions and Function Notation](https://openstax.org/books/precalculus-2e/pages/1-1-functions-and-function-notation)).
- LibreTexts destaca que al multiplicar o dividir una desigualdad por un
  número negativo se invierte el signo
  ([Solving One-Step Inequalities](https://math.libretexts.org/Bookshelves/Applied_Mathematics/Developmental_Math_%28NROC%29/10%3A_Solving_Equations_and_Inequalities/10.02%3A_Solving_Inequalities/10.2.01%3A_Solving_One-Step_Inequalities)).

## Qué se validó

Se ejecutaron diez preguntas independientes contra el servicio real con
PEP-Plan-RAG v3 y el generador local determinista de emergencia. Se verificó
que la respuesta contuviera la relación matemática esencial, no solo una
respuesta vacía. Los temas fueron: dominio racional, valor absoluto de
√(x²), dominio de logaritmos, desigualdades con divisor negativo,
composición de funciones, inversas, leyes de exponentes, grados/radianes,
factorización y matrices.

También se conservó el banco de regresión conversacional de 38 escenarios y
191 turnos, que incluye respuestas cortas como «no», «7», «¿y luego?» y
referencias como «eso».

## Resultado

```text
Casos informados por fuentes: 10
Casos fallidos: 0
Regresión conversacional: 38 escenarios / 191 turnos / 0 fallos
```

Resultados detallados: [`web_informed_scenarios.json`](../data/evaluation/web_informed_scenarios.json).

## Correcciones aplicadas

1. Una pregunta matemática completa es la autoridad del turno. El historial
   solo se agrega al prompt local cuando el mensaje es realmente corto o usa
   una referencia («eso», «¿por qué?», «¿y luego?»). Esto evita que un tema
   anterior, por ejemplo composición, contamine una nueva desigualdad.
2. Se añadieron respuestas locales auditables para composición, inversas,
   logaritmos, √(x²), exponentes, trigonometría en grados, desigualdades con
   signo invertido y signos de una factorización.
3. El banco comprueba explícitamente relaciones matemáticas, no únicamente
   que exista texto. Las respuestas de proveedores remotos siguen pasando por
   las mismas guardas y tienen el fallback local disponible.

## Reproducción

```bash
PYTHONPATH=src .venv/bin/python scripts/validate_web_informed_scenarios.py
PYTHONPATH=src .venv/bin/python scripts/validate_context_regressions.py
PYTHONPATH=src .venv/bin/pytest -q
```

La prueba no demuestra corrección universal. Es una barrera de regresión para
los errores observados; antes de una prueba con estudiantes se debe ampliar el
conjunto con ejercicios revisados por docentes y una rúbrica pedagógica.
