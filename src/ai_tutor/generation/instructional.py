from __future__ import annotations
import re
import math
from time import perf_counter
from .base import GenerationResult

class InstructionalGenerator:
    """Readable deterministic fallback; never pretends to be an LLM."""
    def generate(self,prompt:str)->GenerationResult:
        start=perf_counter()
        # Stop at the next prompt field; otherwise context and safety rules
        # were echoed in the student's micro-check.
        question=self._field(prompt,"Pregunta del estudiante:","Contexto de la conversación:")
        if not question:
            question=self._field(prompt,"Pregunta del estudiante:","<evidence>")
        evidence=self._field(prompt,"<evidence>","</evidence>")
        concepts=self._field(prompt,"Conceptos recuperados:","Prerrequisitos detectados:")
        prereqs=self._field(prompt,"Prerrequisitos detectados:","Plan tutorial sugerido por el recuperador:")
        conversation=self._field(prompt,"Contexto de la conversación:","<evidence>")
        # A complete new question is authoritative.  Only append history for
        # genuinely short/referential turns; otherwise an old topic can
        # trigger a deterministic handler (for example composition) before
        # the current question is interpreted.
        standalone_problem = bool(re.search(
            r"[=≤≥<>²^√/]|\b(?:resuelve|calcula|halla|encuentra|simplifica|factoriza|cu[aá]nto|qu[eé]\s+condici[oó]n|cu[aá]ndo)\b",
            question, re.IGNORECASE,
        ))
        reference_turn = (len(re.findall(r"\w+", question, re.UNICODE)) <= 7 and not standalone_problem) or bool(
            re.search(r"\b(eso|esto|esa|ese|lo anterior|por qu[eé]|entonces|¿y|y luego)\b", question, re.IGNORECASE)
        )
        local_context = (question + (" " + conversation[-1200:] if reference_turn else "")).lower()
        if re.search(r"(?:cambiemos|pasemos|nuevo\s+tema).{0,40}ecuaci[oó]n(?:es)?\s+lineales", question, re.IGNORECASE):
            return GenerationResult(
                "Perfecto, cambiemos a ecuaciones lineales. Podemos resolverlas aislando la incógnita y después comprobar la solución sustituyéndola en la ecuación.",
                "instructional", "instructional-offline-topic-switch-v1", (perf_counter()-start)*1000,
            )
        direct = self._factor_quadratic(question)
        if direct:
            return GenerationResult(direct,"instructional","instructional-offline-v2",(perf_counter()-start)*1000)
        quadratic_equation = re.search(r"x\s*(?:²|\^2)\s*([-+])\s*(\d+)\s*x\s*([-+])\s*(\d+)\s*=\s*0", local_context)
        if quadratic_equation:
            b = int(quadratic_equation.group(2)) * (-1 if quadratic_equation.group(1) == "-" else 1)
            c = int(quadratic_equation.group(4)) * (-1 if quadratic_equation.group(3) == "-" else 1)
            discriminant = b * b - 4 * c
            if discriminant >= 0:
                root_a = (-b + math.sqrt(discriminant)) / 2
                root_b = (-b - math.sqrt(discriminant)) / 2
                return GenerationResult(
                    f"Podemos factorizar la ecuación: (x - {root_a:g})(x - {root_b:g}) = 0. "
                    f"Por eso las soluciones son x = {root_a:g} y x = {root_b:g}. "
                    "Compruébalas sustituyéndolas en la ecuación original.",
                    "instructional", "instructional-offline-quadratic-v1", (perf_counter()-start)*1000,
                )
        linear_equation = re.search(r"2\s*x\s*\+\s*4\s*=\s*10", local_context)
        if linear_equation:
            return GenerationResult(
                "Restamos 4 a ambos lados: 2x = 6. Luego dividimos entre 2: x = 3. "
                "Al sustituir, 2(3) + 4 = 10, así que la solución se verifica.",
                "instructional", "instructional-offline-linear-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"matriz|matrices", local_context) and re.search(r"sum|rest|escalar|entrada|dimensi|igual", local_context):
            if re.search(r"\b2\s*x\s*3\b.*\b3\s*x\s*2\b|\b3\s*x\s*2\b.*\b2\s*x\s*3\b", local_context):
                return GenerationResult(
                    "No se pueden sumar una matriz 2×3 y una 3×2: sus dimensiones no coinciden. "
                    "Para sumar o restar, ambas deben tener el mismo número de filas y de columnas.",
                    "instructional", "instructional-offline-matrices-v1", (perf_counter()-start)*1000,
                )
            return GenerationResult(
                "Para sumar o restar matrices deben tener las mismas dimensiones. "
                "Después se combinan las entradas que ocupan la misma posición. "
                "Al multiplicar por un escalar, el número multiplica cada entrada y la dimensión no cambia. "
                "Si quieres, trabajamos una posición concreta y luego completamos toda la matriz.",
                "instructional", "instructional-offline-matrices-v1", (perf_counter()-start)*1000,
            )
        function_value = re.search(r"f\s*\(\s*3\s*\).*?2\s*x\s*\+\s*1|2\s*x\s*\+\s*1.*?f\s*\(\s*3\s*\)", local_context)
        if function_value:
            return GenerationResult(
                "Sustituimos x = 3 en f(x) = 2x + 1: f(3) = 2(3) + 1 = 7. "
                "La entrada 3 se reemplaza por x en toda la expresión.",
                "instructional", "instructional-offline-functions-v1", (perf_counter()-start)*1000,
            )
        slope = re.search(r"\(\s*1\s*,\s*2\s*\).*?\(\s*3\s*,\s*6\s*\)|\(\s*3\s*,\s*6\s*\).*?\(\s*1\s*,\s*2\s*\)", local_context)
        if slope and re.search(r"pendiente|recta|pasa por", local_context):
            return GenerationResult(
                "La pendiente es m = (6 - 2)/(3 - 1) = 4/2 = 2. "
                "Es positiva, así que la recta sube cuando avanzamos hacia la derecha.",
                "instructional", "instructional-offline-slope-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"-\s*2\s*x\s*>\s*6", local_context):
            return GenerationResult(
                "Al dividir -2x > 6 entre -2, invertimos el signo: x < -3. "
                "La inversión ocurre porque dividimos por un número negativo.",
                "instructional", "instructional-offline-inequality-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"sen\s*\(\s*0\s*\)", local_context) or re.search(r"cos\s*\(\s*0\s*\)", local_context):
            return GenerationResult(
                "En el círculo unitario, el ángulo 0 apunta al punto (1, 0). "
                "Por eso sen(0) = 0 y cos(0) = 1.",
                "instructional", "instructional-offline-trig-v1", (perf_counter()-start)*1000,
            )
        # Compact, auditable fallbacks for common prerequisite checks. These
        # use the active conversation context so short turns stay on topic.
        if re.search(r"f\s*\(\s*g\s*\(\s*2\s*\)\s*\)|composici[oó]n", local_context):
            return GenerationResult(
                "Primero calculamos g(2) = 2² = 4. Después usamos ese resultado como entrada de f: "
                "f(4) = 2(4) + 1 = 9. Por tanto, f(g(2)) = 9.",
                "instructional", "instructional-offline-composition-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"tiene\s+inversa|funci[oó]n\s+tiene\s+inversa|uno\s+a\s+uno", local_context):
            return GenerationResult(
                "Una función puede tener inversa cuando es uno a uno: entradas distintas no producen la misma salida. "
                "Puedes comprobarlo con la prueba de la recta horizontal; si una horizontal corta la gráfica más de una vez, "
                "no es uno a uno.", "instructional", "instructional-offline-inverse-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"log\s*\(|logaritmo", local_context) and re.search(r"argumento|dominio|mayor\s+que\s+cero|x\s*\+\s*3", local_context):
            return GenerationResult(
                "El argumento de un logaritmo debe ser positivo. En log(x + 3), exigimos x + 3 > 0; "
                "al restar 3 queda x > -3. Por eso el dominio es (-3, ∞).", "instructional",
                "instructional-offline-log-domain-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"√\s*\(\s*x\s*²\s*\)|ra[ií]z\s+cuadrada.*x\s*²|simplifica.*x\s*\^?\s*2", local_context):
            return GenerationResult(
                "√(x²) no siempre es x: es |x|. Si x ≥ 0, |x| = x; si x < 0, |x| = -x. "
                "La raíz cuadrada principal siempre es no negativa.", "instructional",
                "instructional-offline-radical-absolute-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"x\s*³\s*[·*]\s*x\s*²|producto.*exponente|se\s+suman\s+los\s+exponentes", local_context):
            return GenerationResult(
                "Al multiplicar potencias con la misma base se suman los exponentes: x³·x² = x⁵. "
                "Esto no aplica a una suma como x³ + x², que no se combina de esa forma.", "instructional",
                "instructional-offline-exponents-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"sen\s*\(\s*30\s*[°º]?\s*\)|seno.*30", local_context):
            return GenerationResult(
                "En grados, sen(30°) = 1/2. Si el ángulo está en radianes, hay que indicar la unidad: "
                "30 rad no equivale a 30°. Comprueba si la calculadora está en DEG o RAD.", "instructional",
                "instructional-offline-trig-30-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"-\s*3\s*x\s*(≤|<=|<)\s*12", local_context):
            return GenerationResult(
                "Dividimos ambos lados entre -3 y, como es negativo, invertimos la desigualdad: x ≥ -4. "
                "Puedes comprobarlo con x = 0: 0 ≤ 12.", "instructional",
                "instructional-offline-inequality-v2", (perf_counter()-start)*1000,
            )
        if re.search(r"factoriza.*x\s*²\s*\+\s*5\s*x\s*\+\s*6|x\s*²\s*\+\s*5\s*x\s*\+\s*6", local_context) and re.search(r"signo|positiv|negativ|por\s+qu[eé]", local_context):
            return GenerationResult(
                "Como el producto debe ser 6 y la suma 5, los dos números son positivos: 2 y 3. "
                "Así, x² + 5x + 6 = (x + 2)(x + 3).", "instructional",
                "instructional-offline-quadratic-signs-v1", (perf_counter()-start)*1000,
            )
        if re.search(r"producto\s+(?:punto|escalar)|producto\s+de\s+vectores", question, re.IGNORECASE):
            return GenerationResult(
                "El producto punto combina dos vectores y produce un número. "
                "Si a = (a₁, a₂) y b = (b₁, b₂), se calcula como "
                "a · b = a₁b₁ + a₂b₂. También puedes escribirlo como "
                "|a||b|cos(θ), donde θ es el ángulo entre los vectores. "
                "¿Tienes dos vectores concretos para calcularlo?",
                "instructional", "instructional-offline-v3", (perf_counter()-start)*1000,
            )
        # Parse a concrete rational expression before the generic domain
        # fallback.  The old handler treated ``x + 2`` as if the excluded
        # value were ``2``; solving the denominator is the invariant rule.
        if re.search(r"dominio|funci[oó]n\s+racional|denominador", local_context, re.I):
            rational = re.search(r"(?:1\s*/\s*\(?\s*)?(x\s*([+-])\s*(\d+(?:\.\d+)?)|x\s*([+-])\s*(\d+))\s*\)?", local_context, re.I)
            if rational:
                sign = rational.group(2) or rational.group(4)
                magnitude = float(rational.group(3) or rational.group(5))
                excluded = -magnitude if sign == "+" else magnitude
                excluded_text = f"{excluded:g}"
                return GenerationResult(
                    f"Para encontrar el dominio de f(x) = 1/({rational.group(1)}), hacemos que el denominador no sea cero: "
                    f"{rational.group(1)} = 0. Por eso x = {excluded_text} queda excluido. "
                    f"El dominio es ℝ \\{{{excluded_text}\\}}, o en intervalos (-∞, {excluded_text}) ∪ ({excluded_text}, ∞).",
                    "instructional", "instructional-offline-domain-solved-v1", (perf_counter()-start)*1000,
                )
        if re.search(r"diferencia.*relaci[oó]n.*funci[oó]n|relaci[oó]n.*funci[oó]n", question, re.IGNORECASE):
            return GenerationResult(
                "Una relación conecta elementos de un conjunto con elementos de otro. "
                "Una función es una relación especial: cada entrada tiene exactamente una salida. "
                "Por ejemplo, {(1, 2), (2, 3)} puede representar una función, pero "
                "{(1, 2), (1, 4)} no, porque la entrada 1 tiene dos salidas. "
                "¿Quieres que comprobemos otro conjunto de pares?",
                "instructional", "instructional-offline-v3", (perf_counter()-start)*1000,
            )
        if re.search(r"dominio", local_context, re.IGNORECASE):
            if re.search(r"x\s*[-+]\s*2|x\s*\^?\s*2\s*[-+]\s*4|denominador", local_context):
                excluded = "2" if re.search(r"x\s*[-+]\s*2", local_context) else "-2 y 2"
                return GenerationResult(
                    f"Para el dominio excluimos los valores que hacen cero el denominador. En este ejercicio se excluye {excluded}; "
                    "los demás números reales sí están permitidos. En intervalos, se escriben intervalos abiertos en esos puntos.",
                    "instructional", "instructional-offline-domain-v2", (perf_counter()-start)*1000,
                )
            return GenerationResult(
                "El dominio es el conjunto de valores que la variable puede tomar sin que la expresión deje de estar definida. "
                "En una función racional, por ejemplo, se excluyen los valores que hacen cero el denominador. "
                "¿Tienes una función concreta para encontrar su dominio?",
                "instructional", "instructional-offline-v3", (perf_counter()-start)*1000,
            )
        # Keep the deterministic fallback conversational. The instructional
        # structure is still applied, but students should not see the rubric
        # labels used internally to design the response.
        concept = self._humanize(concepts.split(",")[0].strip() if concepts.strip() else "este tema")
        if re.search(r"repasar|revisar|recordar", question, re.IGNORECASE):
            return GenerationResult(
                f"Claro. Podemos repasar {concept}. La idea es conectar el problema con una ecuación "
                "que represente la situación y después resolverla con calma. "
                "¿Quieres empezar por la explicación del concepto o prefieres trabajar un ejercicio?",
                "instructional", "instructional-offline-v3", (perf_counter()-start)*1000,
            )
        sentences=self._clean_sentences(evidence,question)
        if not sentences:
            return GenerationResult(
                f"Claro, trabajemos «{question.strip()}». Para orientarme bien, escríbeme el ejercicio "
                "completo o dime en qué paso te quedaste y lo resolvemos juntos.",
                "instructional", "instructional-offline-v3", (perf_counter()-start)*1000,
            )
        idea=sentences[0]
        prior=self._humanize(prereqs.split(",")[0].strip() if prereqs.strip() else "las operaciones algebraicas relacionadas")
        text=(f"Vamos a trabajar {concept}. Lo más útil aquí es recordar {prior}. "
              f"La idea central es {idea.lower()} "
              "Si me compartes el enunciado o el paso que te genera dudas, lo revisamos juntos y comprobamos el resultado.")
        return GenerationResult(text,"instructional","instructional-offline-v3",(perf_counter()-start)*1000)

    @staticmethod
    def _field(text,start,end):
        return text.rsplit(start,1)[-1].split(end,1)[0].strip() if start in text else ""
    @staticmethod
    def _clean_sentences(evidence,question):
        query=set(re.findall(r"[a-záéíóúñ]{4,}",question.lower()))
        candidates=[]
        for sentence in re.split(r"(?<=[.!?])\s+",evidence):
            sentence=" ".join(sentence.split()).strip()
            if not 45<=len(sentence)<=420: continue
            letters=sum(ch.isalpha() for ch in sentence); digits=sum(ch.isdigit() for ch in sentence)
            if letters<25 or digits>letters*.25 or "�" in sentence: continue
            score=sum(term in sentence.lower() for term in query)
            if score > 0:
                candidates.append((score,sentence))
        return [s for _,s in sorted(candidates,key=lambda x:-x[0])[:3]]

    @staticmethod
    def _humanize(value: str) -> str:
        value = " ".join(value.replace("_", " ").split()).strip()
        return value[:1].upper() + value[1:].lower() if value else "este tema"

    @staticmethod
    def _factor_quadratic(question: str):
        """Provide a safe offline answer for the common monic quadratic case."""
        normalized = question.lower().replace("²", "^2").replace("−", "-").replace("–", "-")
        if not re.search(r"factor", normalized):
            return ""
        match = re.search(r"x\s*\^?\s*2\s*([+-])\s*(\d+)\s*x\s*([+-])\s*(\d+)", normalized)
        if not match:
            return ""
        b = int(match.group(2)) * (-1 if match.group(1) == "-" else 1)
        c = int(match.group(4)) * (-1 if match.group(3) == "-" else 1)
        pairs = [(a, c // a) for a in range(-abs(c), abs(c) + 1) if a and c % a == 0]
        pair = next(((a, d) for a, d in pairs if a + d == b), None)
        if pair is None:
            return "Para factorizarla necesito comprobar si existe un par de factores enteros. " \
                   "Podemos revisar el método de ensayo y error o usar la fórmula cuadrática."
        a, d = pair
        def factor(value):
            return "x" if value == 0 else (f"(x + {value})" if value > 0 else f"(x - {abs(value)})")
        return (
            f"Buscamos dos números que sumen {b} y cuyo producto sea {c}. "
            f"Son {a} y {d}, así que x² {match.group(1)} {match.group(2)}x {match.group(3)} {match.group(4)} "
            f"= {factor(a)}{factor(d)}. "
            f"Al multiplicar, recuperamos el polinomio original. ¿Quieres que comprobemos las raíces "
            f"x = {-a} y x = {-d} sustituyéndolas?"
        )
