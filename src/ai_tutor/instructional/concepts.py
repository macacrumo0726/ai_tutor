"""Corpus-grounded seed taxonomy.

Names originate in the book table of contents. Prerequisite edges are explicitly
expert-curated hypotheses, not claims extracted verbatim from the textbook.
"""
from __future__ import annotations
import re
import unicodedata

def slug(text: str) -> str:
    value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")

# (name, topic, prerequisites). This is a conservative initial ontology; the
# builder grounds every retained concept in actual corpus chunks.
SEED_TAXONOMY = [
 ("números reales", "fundamentos", []),
 ("exponentes y radicales", "fundamentos", ["números reales"]),
 ("expresiones algebraicas", "fundamentos", ["números reales"]),
 ("expresiones racionales", "fundamentos", ["expresiones algebraicas"]),
 ("factorización", "fundamentos", ["expresiones algebraicas"]),
 ("ecuaciones", "fundamentos", ["expresiones algebraicas"]),
 ("propiedad del producto cero", "fundamentos", ["factorización", "ecuaciones"]),
 ("ecuaciones cuadráticas", "fundamentos", ["factorización", "ecuaciones"]),
 ("desigualdades", "fundamentos", ["ecuaciones"]),
 ("valor absoluto", "fundamentos", ["números reales"]),
 ("geometría de coordenadas", "geometría analítica", ["números reales"]),
 ("rectas", "geometría analítica", ["geometría de coordenadas", "ecuaciones"]),
 ("funciones", "funciones", ["ecuaciones"]),
 ("dominio", "funciones", ["funciones"]),
 ("rango", "funciones", ["funciones"]),
 ("gráficas de funciones", "funciones", ["funciones", "geometría de coordenadas"]),
 ("transformaciones de funciones", "funciones", ["gráficas de funciones"]),
 ("combinación de funciones", "funciones", ["funciones", "expresiones algebraicas"]),
 ("composición de funciones", "funciones", ["combinación de funciones"]),
 ("función inversa", "funciones", ["funciones", "composición de funciones"]),
 ("funciones polinomiales", "funciones algebraicas", ["funciones", "expresiones algebraicas"]),
 ("funciones racionales", "funciones algebraicas", ["funciones", "expresiones racionales"]),
 ("funciones exponenciales", "funciones trascendentes", ["funciones", "exponentes y radicales"]),
 ("funciones logarítmicas", "funciones trascendentes", ["funciones exponenciales", "función inversa"]),
 ("ángulos", "trigonometría", ["geometría de coordenadas"]),
 ("funciones trigonométricas", "trigonometría", ["funciones", "ángulos"]),
 ("identidades trigonométricas", "trigonometría", ["funciones trigonométricas", "expresiones algebraicas"]),
]

