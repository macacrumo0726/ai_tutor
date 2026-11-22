"""Student-facing learning routes built from the instructional concept graph.

Routes are intentionally broader than individual concepts: a learner sees a
coherent study path (for example, *Fracciones y expresiones algebraicas*) and
can still open any completed route for review.
"""
from __future__ import annotations

import unicodedata


ROUTE_CATALOG = (
    {
        "route_id": "fundamentos_numericos",
        "title": "Fundamentos numéricos",
        "description": "Números reales, operaciones, intervalos y valor absoluto.",
        "terms": ("número", "operación", "intervalo", "valor absoluto", "fracción"),
    },
    {
        "route_id": "fracciones_expresiones",
        "title": "Fracciones y expresiones algebraicas",
        "description": "Simplificación, fracciones algebraicas, exponentes y radicales.",
        "terms": ("fracción", "expresión", "exponente", "radical", "polinomio"),
    },
    {
        "route_id": "ecuaciones_desigualdades",
        "title": "Ecuaciones y desigualdades",
        "description": "Ecuaciones lineales, cuadráticas, valor absoluto y desigualdades.",
        "terms": ("ecuación", "desigualdad", "lineal", "cuadrática", "valor absoluto"),
    },
    {
        "route_id": "funciones_graficas",
        "title": "Funciones y gráficas",
        "description": "Relaciones, dominio, rango, transformaciones y funciones inversas.",
        "terms": ("función", "relación", "dominio", "rango", "gráfica", "inversa"),
    },
    {
        "route_id": "polinomiales_racionales",
        "title": "Funciones polinomiales y racionales",
        "description": "Ceros, factorización, comportamiento y restricciones del dominio.",
        "terms": ("polinomial", "polinomio", "racional", "factorización", "cero real"),
    },
    {
        "route_id": "exponenciales_logaritmicas",
        "title": "Funciones exponenciales y logarítmicas",
        "description": "Crecimiento, leyes de exponentes, logaritmos y sus aplicaciones.",
        "terms": ("exponencial", "logarít", "crecimiento"),
    },
    {
        "route_id": "trigonometria",
        "title": "Trigonometría",
        "description": "Ángulos, razones trigonométricas, identidades y funciones periódicas.",
        "terms": ("trigonom", "seno", "coseno", "tangente", "ángulo"),
    },
)


def _matches(concept: dict, terms: tuple[str, ...]) -> bool:
    haystack = " ".join(str(concept.get(key, "")) for key in
                        ("concept_name", "canonical_name", "topic", "subtopic", "keywords"))
    def plain(value: str) -> str:
        value = unicodedata.normalize("NFKD", value.lower())
        return "".join(char for char in value if not unicodedata.combining(char))
    haystack = plain(haystack)
    return any(plain(term) in haystack for term in terms)


def build_learning_routes(concepts: list[dict], student_state, mastery_threshold: float = .65):
    """Build route-level progress from concept mastery.

    A route is included only when the corpus contains matching concepts. Empty
    routes are therefore not presented as fake progress to a student.
    """
    routes = []
    for definition in ROUTE_CATALOG:
        matched = [item for item in concepts if _matches(item, definition["terms"])]
        if not matched:
            continue
        concept_ids = [item["concept_id"] for item in matched if item.get("concept_id")]
        # A new participant has no observed mastery yet.  Do not display the
        # model's neutral prior (usually 0.50) as if the learner had completed
        # half of every route.
        values = []
        for item in matched:
            cid = item.get("concept_id")
            if not cid:
                continue
            if cid in student_state.concept_mastery:
                values.append(float(student_state.mastery_for(cid, item.get("concept_name", ""))))
            elif any(keyword.lower() in f"{cid} {item.get('concept_name', '')}".lower()
                     for keyword in student_state.gap_keywords):
                values.append(0.20)
            else:
                values.append(0.0)
        progress = sum(values) / len(values) if values else 0.0
        completed = sum(value >= mastery_threshold for value in values)
        routes.append({
            "route_id": definition["route_id"],
            "title": definition["title"],
            "description": definition["description"],
            "progress": round(progress, 3),
            "completed_concepts": completed,
            "total_concepts": len(values),
            "status": "completed" if progress >= mastery_threshold else ("next" if progress > 0 else "available"),
            "concept_ids": concept_ids,
        })
    routes.sort(key=lambda item: (item["status"] == "completed", -item["progress"], item["title"]))
    return routes
