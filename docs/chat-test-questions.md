# Preguntas para probar el tutor de Precálculo

## 1. Preguntas directas

1. ¿Qué es una función?
2. ¿Cuál es la diferencia entre dominio y rango?
3. ¿Qué significa que una función sea uno a uno?
4. ¿Qué es una función inversa?
5. ¿Qué es una asíntota vertical?
6. ¿Qué diferencia hay entre una ecuación y una identidad?
7. ¿Qué representa la pendiente de una recta?
8. ¿Qué es el valor absoluto?

## 2. Preguntas procedimentales

9. ¿Cómo encuentro el dominio de una función racional?
10. ¿Cómo encuentro el rango de una función?
11. ¿Cómo resuelvo x² − 5x + 6 = 0?
12. ¿Cómo factorizo x² + 7x + 12?
13. ¿Cómo resuelvo 2x + 5 = 17?
14. ¿Cómo encuentro la ecuación de una recta que pasa por dos puntos?
15. ¿Cómo encuentro la inversa de f(x) = 2x + 3?
16. ¿Cómo simplifico √50?
17. ¿Cómo resuelvo una desigualdad con valor absoluto?
18. ¿Cómo sumo dos funciones?

## 3. Preguntas sobre prerrequisitos

19. ¿Qué necesito saber antes de aprender ecuaciones cuadráticas?
20. ¿Qué conocimientos previos necesito para entender funciones racionales?
21. ¿Qué debería dominar antes de estudiar logaritmos?
22. ¿Qué debo saber antes de aprender trigonometría?
23. ¿Por qué necesito entender exponentes antes de estudiar logaritmos?
24. ¿Qué conocimientos de álgebra necesito para encontrar el dominio de una función?
25. ¿Qué relación existe entre factorización y ecuaciones cuadráticas?
26. ¿Por qué la propiedad del producto cero sirve para encontrar raíces?

Estas preguntas deberían mostrar diferencias más claras entre RAG, Graph-RAG y
PEP-Plan-RAG.

## 4. Concepciones erróneas

27. ¿El dominio de una función racional excluye los ceros del numerador?
28. ¿Las raíces de x² − 5x + 6 son 5 y 6?
29. ¿Siempre se cumple que √(a+b) = √a + √b?
30. ¿Puedo cancelar cualquier término que aparezca arriba y abajo en una fracción?
31. ¿Una función puede tener dos valores de salida para la misma entrada?
32. ¿La función inversa es lo mismo que 1/f(x)?
33. ¿Todo número elevado a cero es cero?
34. ¿log(a+b) es igual a log(a) + log(b)?
35. ¿Una asíntota vertical significa que la función nunca puede cruzar esa recta?
36. ¿Si una ecuación tiene x², siempre tiene dos soluciones reales?

## 5. Preguntas con errores del estudiante

37. Resolví x² − 5x + 6 = 0 y obtuve x = 5 y x = 6. ¿Está bien?
38. Para encontrar el dominio de 1/(x−3), dije que x no puede ser 0. ¿Qué hice mal?
39. Simplifiqué √12 como √6 + √6. ¿Es correcto?
40. Para invertir f(x) = 2x + 3 escribí 1/(2x+3). ¿Está bien?
41. Factoricé x² + 5x + 6 como (x+1)(x+6). ¿Dónde está el error?
42. Dije que el rango de f(x)=x² son todos los números reales. ¿Es correcto?
43. Cancelé la x en (x+2)/x y obtuve 2. ¿Se puede hacer?
44. Resolví |x|=−3 y obtuve x=3. ¿Está bien?

Estas preguntas permiten evaluar diagnóstico y tratamiento de concepciones
erróneas.

## 6. Preguntas de varios pasos

45. Encuentra el dominio y las asíntotas de f(x) = (x+1)/(x−2).
46. Factoriza x² − 7x + 12 y encuentra sus raíces.
47. Encuentra la inversa de f(x) = (3x−2)/5 y verifica el resultado.
48. Determina el dominio, interceptos y comportamiento de f(x)=1/(x²−4).
49. Resuelve 2x² − 8 = 0 usando factorización.
50. Encuentra la ecuación de la recta que pasa por (2,3) y (5,9).
51. Resuelve |2x−3|≤5 y representa la solución en la recta numérica.
52. Simplifica (x²−9)/(x−3) e indica las restricciones del dominio.

## 7. Pruebas de perfiles en PEP-Plan-RAG v3

Utilizar exactamente la misma pregunta cambiando únicamente el perfil del
estudiante.

### Caso A: ecuaciones cuadráticas

**Pregunta:**

> ¿Cómo resuelvo x² − 5x + 6 = 0?

Probar con:

- Estado desconocido.
- Dominio alto.
- Brecha de álgebra.
- Posible concepción errónea.

### Caso B: funciones racionales

**Pregunta:**

> ¿Cómo encuentro el dominio de f(x)=(x+1)/(x²−4)?

Probar con:

- Estado desconocido.
- Dominio alto.
- Brecha de álgebra.
- Brecha de prerrequisitos.

### Caso C: radicales

**Pregunta:**

> ¿Cómo simplifico √72?

Probar con:

- Estado desconocido.
- Dominio alto.
- Brecha de álgebra.
- Posible concepción errónea.

En cada caso observar si cambian:

- prerrequisitos recuperados;
- chunks seleccionados;
- ruta de aprendizaje;
- cantidad de explicación;
- micro-check;
- contenido innecesario.

## 8. Pruebas de robustez

Ejecutar la misma pregunta usando diferentes formulaciones.

### Formal

> ¿Cómo se determina el dominio de una función racional?

### Conversacional

> ¿Me ayudas a encontrar el dominio de una función racional?

### Informal

> No entiendo eso del dominio cuando hay fracciones, ¿cómo se hace?

### Con error ortográfico

> Como encuentro el domnio de una funcion racional?

### Ambigua

> ¿Cómo saco el dominio?

Un buen resultado debería mantener el concepto central y solicitar aclaración
cuando la pregunta no contiene información suficiente.

## 9. Prueba corta recomendada

Para una primera comparación manual, utilizar:

1. ¿Cómo encuentro el dominio de una función racional?
2. ¿Cómo resuelvo x² − 5x + 6 = 0?
3. ¿Qué conocimientos previos necesito para comprender logaritmos?
4. ¿La función inversa es lo mismo que 1/f(x)?
5. Factoricé x² + 5x + 6 como (x+1)(x+6). ¿Dónde está el error?

Ejecutar cada pregunta con:

```text
RAG
Graph-RAG
PEP-SA-RAG v2
PEP-Plan-RAG v3
```

Comparar:

- corrección matemática;
- naturalidad;
- evidencia recuperada;
- conceptos encontrados;
- prerrequisitos;
- detección del error;
- nivel de andamiaje;
- micro-check;
- latencia.

## 10. Registro sugerido

| Pregunta | Método | Perfil | Correcta | Natural | Prerrequisitos útiles | Andamiaje | Micro-check | Latencia | Notas |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| | | | | | | | | | |
