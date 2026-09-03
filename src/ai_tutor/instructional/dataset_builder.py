from __future__ import annotations
import re
from collections import defaultdict
from pathlib import Path
from .concepts import SEED_TAXONOMY, slug
from .schema import Chunk, Concept, InstructionalUnit, Question

TYPE_PATTERNS = [("worked_example", r"\bejemplo\b"), ("exercise", r"\bejercicio"),
                 ("definition", r"\bdefinici[oó]n\b"), ("theorem", r"\bteorema\b"),
                 ("formula", r"\bf[oó]rmula\b"), ("summary", r"\brepaso|resumen\b")]

def classify_chunk(text: str) -> str:
    low = text.lower()
    return next((kind for kind, pattern in TYPE_PATTERNS if re.search(pattern, low)), "explanation")

def build_from_legacy(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    specs = {slug(name): (name, topic, [slug(p) for p in prereqs]) for name, topic, prereqs in SEED_TAXONOMY}
    aliases = {cid: {name.lower(), cid.replace("_", " ")} for cid, (name, _, _) in specs.items()}
    chunk_map: dict[str, list[str]] = defaultdict(list); page_map: dict[str, set[int]] = defaultdict(set)
    chunks=[]
    for row in rows:
        text=str(row.get("text", "")); low=text.lower()
        found=[cid for cid,names in aliases.items() if any(name in low for name in names)]
        for cid in found:
            chunk_map[cid].append(str(row["chunk_id"])); page_map[cid].update(range(int(row.get("start_page",0)),int(row.get("end_page",0))+1))
        chapter=str(row.get("chapter_title", ""))
        chunks.append(Chunk(str(row["chunk_id"]), text, int(row.get("start_page",0)), int(row.get("end_page",0)), chapter, chapter, "", found, "mixed", classify_chunk(text), "Stewart et al., Precálculo, 6a ed.").to_dict())
    # Retain the corpus-derived taxonomy seeds even if OCR prevents literal matching;
    # their source status remains explicit and source_chunks may be empty.
    successors=defaultdict(list)
    for cid,(_,_,pres) in specs.items():
        for pre in pres: successors[pre].append(cid)
    concepts=[]; units=[]; questions=[]
    for idx,(cid,(name,topic,pres)) in enumerate(specs.items()):
        refs=chunk_map[cid][:20]; pages=sorted(page_map[cid])[:50]
        concept=Concept(cid,name,name,f"Concepto de {name} dentro de {topic}.",topic,name,"mixed",f"Comprender y aplicar {name}.",pres,successors[cid],[*aliases[cid]],[],pages,refs,{"concept_name":"corpus","description":"generated","prerequisites":"expert_curated"})
        concept.validate(); concepts.append(concept.to_dict())
        excerpt=next((c["text"][:700] for c in chunks if c["chunk_id"] in refs), "")
        unit=InstructionalUnit(f"iu_{cid}",cid,concept.learning_objective,pres,excerpt,"","",[],f"¿Qué sabes sobre {name}?",f"Explica o aplica {name}.","Identifica los datos y la meta.","Relaciona la pregunta con la definición.","Divide el procedimiento en pasos.","", "mixed",{"chunk_ids":refs[:3],"pages":pages[:5]}, {"concept_explanation":"corpus" if excerpt else "generated","questions":"generated","prerequisite_concepts":"expert_curated"})
        unit.validate(); units.append(unit.to_dict())
        split=("test" if idx%5==0 else "validation" if idx%5==1 else "train")
        q=Question(f"q_{cid}",f"¿Cómo se define y se aplica {name}?",excerpt[:300] or f"Se requiere una explicación correcta de {name}.",cid,[cid],pres,"mixed","conceptual","generated_from_corpus_taxonomy",split,refs[:2],[cid],pres)
        questions.append(q.to_dict())
    return chunks,concepts,units,questions

