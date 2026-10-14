from __future__ import annotations
import uuid
from .schema import MicroCheck


BANK=(
 ("dominio","Para f(x)=1/(x−3), ¿qué valor debe excluirse del dominio?","3","numeric_equivalence",["Iguala el denominador a cero.","Resuelve x−3=0.","El valor excluido es x=3."]),
 ("factorizacion","¿Qué número completa la factorización (x−2)(x−__)=x²−5x+6?","3","numeric_equivalence",["Busca dos números cuyo producto sea 6.","Además, su suma debe ser 5.","Los números son 2 y 3."]),
 ("ecuacion_lineal","Resuelve 2x+4=10. ¿Cuánto vale x?","3","numeric_equivalence",["Resta 4 en ambos lados.","Obtienes 2x=6.","Divide entre 2."]),
 ("ecuaciones_lineales","Resuelve 2x+4=10. ¿Cuánto vale x?","3","numeric_equivalence",["Resta 4 en ambos lados.","Obtienes 2x=6.","Divide entre 2."]),
 ("exponente","Calcula 2³.","8","numeric_equivalence",["Escribe 2³ como producto.","2×2×2.","El resultado es 8."]),
 ("radical","¿Cuál es la raíz cuadrada principal de 49?","7","numeric_equivalence",["Busca el número positivo cuyo cuadrado es 49.","7×7=49.","La raíz principal es 7."]),
 ("funcion","En la notación f(3)=7, ¿cuál es la entrada?","3","numeric_equivalence",["La entrada aparece dentro del paréntesis.","Observa f(3).", "La entrada es 3."]),
 ("cuadratica","¿Cuántas raíces reales distintas tiene x²−5x+6=0?","2","numeric_equivalence",["Factoriza el trinomio.","(x−2)(x−3)=0.","Hay dos raíces distintas."]),
)


def build_micro_check(concept_id: str, concept_name: str = "") -> MicroCheck:
    searchable=f"{concept_id} {concept_name}".lower()
    selected=next((row for row in BANK if row[0] in searchable),None)
    if selected:
        _,question,answer,validator,hints=selected
    else:
        label=(concept_name or concept_id).replace("_"," ")
        question=f"En una frase, explica la idea central de {label}."
        tokens=[token for token in label.lower().split() if len(token)>3][:3]
        answer="|".join(tokens) or label.lower(); validator="keyword_rubric"
        hints=[f"Recuerda la definición de {label}.","Menciona qué representa y para qué se usa.",f"Incluye estas ideas: {', '.join(tokens)}."]
    return MicroCheck(f"mc_{uuid.uuid4().hex}",concept_id,question,answer,
                      "numeric" if validator=="numeric_equivalence" else "short_text",
                      validator,hints)
