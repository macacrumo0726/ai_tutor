# Avance PATI: memoria, editor matemático y validación de respuestas

Fecha: 14 de octubre de 2026

## 1. Problemas revisados

Se revisó un caso en el que el estudiante respondió `8` a la pregunta sobre
qué valor hace cero el denominador de `1/(x - 5)`. PATI respondió de forma
incorrecta que la respuesta era correcta.

La auditoría de la base de datos confirmó que la memoria sí estaba funcionando:
el prompt enviado al generador incluía el ejercicio anterior, la pregunta del
tutor y la respuesta `8`. El problema no era pérdida de contexto, sino que el
LLM no tenía una verificación matemática determinista antes de generar la
retroalimentación.

La evaluación anterior clasificaba la respuesta como `unscored`, porque no
existía una respuesta esperada registrada. Esto impedía actualizar el dominio,
pero no impedía que el modelo elogiara una respuesta incorrecta.

## 2. Corrección matemática determinista

Se agregó:

```text
src/ai_tutor/assessment/response_verifier.py
```

La primera versión verifica de forma auditable micro-checks del tipo:

```text
x - a = 0  →  x = a
x + a = 0  →  x = -a
```

Para el caso observado:

```text
Ejercicio:           1/(x - 5)
Respuesta estudiante: 8
Valor esperado:       5
Resultado:            incorrecto
Confianza:            0.99
```

Cuando el verificador detecta una respuesta incorrecta, PATI ya no depende de
que el LLM la corrija. Se utiliza una respuesta segura y pedagógica:

```text
Revisemos esa respuesta: si sustituyes x = 8, el denominador no queda en cero.
Para encontrar el valor que debemos excluir, resolvemos x - 5 = 0.
Por eso el valor correcto es x = 5, no 8.
¿Puedes comprobarlo sustituyendo ese valor en el denominador?
```

La evidencia se registra como:

```text
evidence_type: verified_conversational_response
source: deterministic_math_verifier
outcome: 0.0
```

Esto permite actualizar el perfil sólo cuando la respuesta tiene una
verificación objetiva.

Las respuestas que no pertenecen a una regla soportada permanecen sin
calificar. En esos casos PATI recibe la instrucción de no afirmar que la
respuesta es correcta sin comprobarla explícitamente.

## 3. Memoria y trazabilidad

La memoria conversacional continúa funcionando por usuario y conversación.
Antes de cada pregunta se recuperan:

- resumen de la conversación;
- problema activo;
- últimos turnos;
- respuesta previa del tutor;
- conceptos recuperados anteriormente.

La consulta enviada al retriever se contextualiza cuando el estudiante escribe
respuestas breves como `8`, `2` o `¿y ahora?`.

Las conversaciones nuevas permanecen aisladas. Un usuario recién registrado
empieza con historial vacío en la API. El frontend crea únicamente una
conversación nueva sin mensajes para permitir comenzar el chat.

## 4. Editor matemático

El botón `Σ` del compositor abre un teclado matemático con plantillas editables:

```text
Potencia:       □^(□)
Raíz:           √(□)
Fracción:       (□)/(□)
Valor absoluto: |□|
Función:        f(□)
Seno:           sen(□)
Coseno:         cos(□)
```

El estudiante escribe sobre cada `□` y puede usar `Tab` para pasar al siguiente
espacio. También incluye símbolos como `≤`, `≥`, `π`, `θ` e `∞`.

No se permite enviar una fórmula con espacios `□` incompletos. La notación
utilizada es lineal y compatible con el prompt del tutor, por ejemplo:

```text
f(x)=1/(x-2)
3^(4)
√(x+1)
```

Una futura iteración puede incorporar MathLive o KaTeX para edición y
renderizado visual más avanzado.

## 5. Vista de investigación

La vista administrativa permite seleccionar un estudiante y consultar:

- dominio por concepto;
- confianza;
- número de evidencias;
- conversaciones archivadas y activas;
- mensajes completos de cada conversación;
- evaluaciones heurísticas;
- perfil longitudinal.

Ruta:

```text
http://localhost:3000/admin
```

Cuenta de demostración:

```text
Usuario: investigador_demo
PIN: Investiga1234
```

## 6. Persistencia local observada

Base de datos:

```text
data/app/ai_tutor.sqlite3
```

Durante la revisión se observaron estos registros locales:

```text
Usuarios:          4
Conversaciones:    9
Mensajes:          70
Registros dominio: 9
Evidencias:        9
```

Las pruebas también verifican que un segundo usuario no puede consultar la
conversación del primero.

## 7. Validación ejecutada

```text
69 pruebas Python aprobadas
TypeScript correcto
ESLint correcto
Build de producción correcto
```

Las pruebas nuevas cubren:

- saludo sin activar retrieval;
- respuestas numéricas correctas e incorrectas;
- denominadores `x - a` y `x + a`;
- preguntas no soportadas que permanecen sin calificar;
- actualización del dominio con evidencia verificada;
- aislamiento entre usuarios;
- historial persistente para investigación;
- plantillas matemáticas incompletas.

## 8. Commits de este bloque

```text
292a6d2 feat: add math input and research history viewer
4de6b18 fix: verify short math answers before tutor feedback
```

La rama de trabajo quedó subida a GitHub:

```text
feature/cloud-web-app
```

## 9. Pendientes para la siguiente sesión

1. Extender el verificador a ecuaciones, desigualdades, raíces y respuestas
   algebraicas equivalentes.
2. Evaluar MathLive frente al teclado lineal actual.
3. Añadir una interfaz visible de “respuesta verificada” en modo estudiante,
   sin mostrar trazas internas.
4. Migrar sesiones en memoria y SQLite a servicios administrados antes de Azure.
5. Probar el flujo completo con participantes reales y consentimiento informado.
