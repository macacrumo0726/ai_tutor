"""Corpus-wide instructional database builder driven by the PDF table of contents."""
from __future__ import annotations
import re
from collections import defaultdict
from dataclasses import asdict
from typing import Any
from .concepts import slug

EXCLUDE = re.compile(
    r"(?i)\b(ejercicios|repaso|examen|respuestas|índice|descripci[oó]n del cap[ií]tulo)\b"
)
SECTION_RE = re.compile(r"^(\d+)\.(\d+)\s+(.+)$")
CHAPTER_RE = re.compile(r"(?i)^CAP[IÍ]TULO\s+(\d+)\s+(.+)$")

def clean_title(title: str) -> str:
    return " ".join(title.replace("\r", " ").split()).strip(" .")

def extract_passage(text: str, marker: str, limit: int = 900) -> str:
    match = re.search(marker, text, flags=re.I)
    if not match:
        return ""
    passage = text[match.start(): match.start() + limit]
    return " ".join(passage.split())

def classify_chunk(text: str) -> str:
    low = text.lower()
    patterns = [
        ("worked_example", r"\bejemplo\s+\d+"), ("exercise", r"\bejercicios?\b"),
        ("definition", r"\bdefinici[oó]n\b"), ("theorem", r"\bteorema\b"),
        ("formula", r"\bf[oó]rmula\b"), ("summary", r"\brepaso|resumen\b"),
    ]
    return next((kind for kind, pattern in patterns if re.search(pattern, low)), "explanation")

def toc_records(toc: list[list[Any]], page_count: int) -> list[dict]:
    """Convert PDF bookmarks into bounded records with chapter/section ancestry."""
    records=[]; chapter=None; section=None
    for i,(level,raw,page) in enumerate(toc):
        title=clean_title(raw); end=(toc[i+1][2]-1 if i+1<len(toc) else page_count)
        if level==2:
            match=CHAPTER_RE.match(title)
            chapter={"number":int(match.group(1)),"title":match.group(2)} if match and int(match.group(1))<=13 else None
            section=None
        elif level==3 and chapter:
            match=SECTION_RE.match(title)
            section={"number":f"{match.group(1)}.{match.group(2)}","title":match.group(3)} if match else None
        if chapter:
            records.append({"level":level,"title":title,"page_start":int(page),"page_end":max(int(page),int(end)),"chapter":chapter.copy(),"section":section.copy() if section else None})
    return records

def build_database(toc: list[list[Any]], page_texts: list[str], legacy_rows: list[dict]):
    records=toc_records(toc,len(page_texts)); instructional=[r for r in records if r["level"] in (3,4) and not EXCLUDE.search(r["title"])]
    # IDs are stable and prefixed with section numbers where available.
    concepts=[]; record_by_id={}; siblings=defaultdict(list)
    for record in instructional:
        section=record["section"]; prefix=section["number"] if section else str(record["chapter"]["number"])
        display_title=section["title"] if record["level"]==3 and section else record["title"]
        record["display_title"]=display_title
        cid=slug(f"{prefix}_{display_title}")
        if cid in record_by_id: cid=f"{cid}_p{record['page_start']}"
        record["concept_id"]=cid; record_by_id[cid]=record
        siblings[(record["chapter"]["number"],section["number"] if section else "")].append(cid)

    # Rebuild page-accurate chunks from the PDF. The legacy chunk page metadata
    # is unusable (almost every row spans pages 6-1014), so legacy rows remain
    # preserved but are not treated as authoritative alignment data.
    chunk_rows=[]; concept_chunks=defaultdict(list); concept_pages=defaultdict(set); concept_text=defaultdict(list)
    ordered=sorted(instructional,key=lambda r:(r["page_start"],r["level"])); all_ordered=sorted(records,key=lambda r:(r["page_start"],r["level"]))
    section_ids={r["section"]["number"]:r["concept_id"] for r in ordered if r["level"]==3 and r["section"]}
    first_page=min((r["page_start"] for r in records),default=1)
    last_page=min(max((r["page_end"] for r in records),default=len(page_texts)),len(page_texts))
    for page in range(first_page,last_page+1):
        text=" ".join(page_texts[page-1].split())
        if not text: continue
        matches=[r for r in all_ordered if r["page_start"]<=page<=r["page_end"]]
        active=max(matches,key=lambda r:r["level"]) if matches else None
        active_instructional=[r for r in matches if r in instructional]
        chosen=max(active_instructional,key=lambda r:r["level"]) if active_instructional else None
        cids=[]
        if chosen:
            cids=[r["concept_id"] for r in active_instructional]
            for record in active_instructional:
                if record["level"]==4 and record["section"]:
                    parent=next((r for r in ordered if r["level"]==3 and r["section"] and r["section"]["number"]==record["section"]["number"]),None)
                    if parent:cids.append(parent["concept_id"])
        elif active and active.get("section") and active["section"]["number"] in section_ids:
            cids=[section_ids[active["section"]["number"]]]
        section=(chosen or active).get("section") if (chosen or active) else None
        chapter=(chosen or active).get("chapter") if (chosen or active) else None
        words=text.split(); size=350; overlap=50; step=size-overlap
        for local,start_word in enumerate(range(0,len(words),step)):
            part=" ".join(words[start_word:start_word+size])
            if len(part.split())<25: continue
            cid_value=f"p{page:04d}_chunk{local:02d}"
            enriched={"chunk_id":cid_value,"text":part,"page_start":page,"page_end":page,
                      "section":section["number"] if section else "","topic":chapter["title"] if chapter else "",
                      "subtopic":chosen["title"] if chosen else active["title"] if active else "","concept_ids":list(dict.fromkeys(cids)),"difficulty":"mixed",
                      "chunk_type":classify_chunk(part),"source":"Stewart, Redlin y Watson, Precálculo, 6a ed."}
            chunk_rows.append(enriched)
            for cid in cids:
                concept_chunks[cid].append(cid_value); concept_pages[cid].add(page); concept_text[cid].append(part)

    relations=[]; predecessors={}
    # Conservative sequence edges: previous section/topic is NEXT_CONCEPT and an inferred prerequisite candidate.
    for group,ids in siblings.items():
        for previous,current in zip(ids,ids[1:]):
            predecessors.setdefault(current,[]).append(previous)
            relations.extend([
              {"source_id":previous,"target_id":current,"edge_type":"NEXT_CONCEPT","weight":1.0,"source":"pdf_toc_order","confidence":1.0},
              {"source_id":previous,"target_id":current,"edge_type":"PREREQUISITE_OF","weight":0.55,"source":"inferred_from_instructional_sequence","confidence":0.55},
            ])
    successors=defaultdict(list)
    for rel in relations:
        if rel["edge_type"]=="PREREQUISITE_OF": successors[rel["source_id"]].append(rel["target_id"])

    units=[]; questions=[]
    for position,record in enumerate(instructional):
        cid=record["concept_id"]; title=record["display_title"]; texts=concept_text[cid]
        combined=" ".join(texts); explanation=" ".join(combined.split())[:1200]
        worked=extract_passage(combined,r"\bEJEMPLO\s+\d+",1200)
        exercise=extract_passage(combined,r"\bEJERCICIOS?\b",800)
        worked_value=worked or f"Ejemplo instruccional generado: plantea un caso representativo de {title.lower()}, identifica los datos, aplica la definición o procedimiento pertinente y verifica el resultado."
        solution_value=worked or f"Solución orientativa generada: identifica el objetivo, recupera la definición de {title.lower()}, desarrolla los pasos justificándolos y comprueba que el resultado satisface las condiciones del problema."
        prereqs=predecessors.get(cid,[])
        concept={"concept_id":cid,"concept_name":title,"canonical_name":title.lower(),"description":explanation[:500] or f"Tema {title} identificado en el índice del libro.",
          "topic":record["chapter"]["title"],"subtopic":record["section"]["title"] if record["section"] else title,
          "difficulty":"mixed","learning_objective":f"Comprender, representar y aplicar {title.lower()}.","prerequisites":prereqs,
          "successors":successors[cid],"keywords":list(dict.fromkeys(re.findall(r"\w+",title.lower()))),"aliases":[],
          "source_pages":sorted(concept_pages[cid]),"source_chunks":list(dict.fromkeys(concept_chunks[cid])),
          "provenance":{"concept_name":"corpus","description":"corpus" if explanation else "generated","learning_objective":"generated","prerequisites":"inferred"},
          "toc_level":record["level"],"chapter_number":record["chapter"]["number"],"section_number":record["section"]["number"] if record["section"] else ""}
        concepts.append(concept)
        units.append({"instructional_unit_id":f"iu_{cid}","concept_id":cid,"learning_objective":concept["learning_objective"],
          "prerequisite_concepts":prereqs,"concept_explanation":explanation,"worked_example":worked_value,
          "guided_example":f"Analiza un caso de {title.lower()}: identifica los datos, selecciona la representación y justifica cada paso.",
          "common_misconceptions":[f"Confundir la definición de {title.lower()} con un procedimiento relacionado.","Aplicar una regla sin comprobar sus condiciones."],
          "diagnostic_question":f"¿Qué conocimientos previos usarías para trabajar con {title.lower()}?",
          "practice_question":exercise[:500] or f"Explica con un ejemplo cómo se aplica {title.lower()}.",
          "hint_level_1":"Identifica qué se conoce y qué se debe encontrar.","hint_level_2":f"Relaciona el problema con la definición de {title.lower()}.",
          "hint_level_3":"Escribe el procedimiento en pasos y verifica cada condición.","solution":solution_value,
          "difficulty":"mixed","source_reference":{"pages":sorted(concept_pages[cid]),"chunk_ids":list(dict.fromkeys(concept_chunks[cid]))},
          "provenance":{"concept_explanation":"corpus" if explanation else "generated","worked_example":"corpus" if worked else "generated",
                        "guided_example":"generated","common_misconceptions":"inferred","diagnostic_question":"generated","practice_question":"corpus" if exercise else "generated","solution":"corpus" if worked else "generated"}})
        split="test" if position%10==0 else "validation" if position%10==1 else "train"
        gold=list(dict.fromkeys(concept_chunks[cid]))[:3]
        question_specs=[
          ("conceptual",f"¿Qué significa {title.lower()} y cuáles son sus elementos principales?"),
          ("procedural",f"¿Cómo se resuelve paso a paso un problema de {title.lower()}?"),
          ("prerequisite",f"¿Qué conocimientos previos se necesitan para comprender {title.lower()}?"),
        ]
        for qn,(qtype,prompt) in enumerate(question_specs,1):
            questions.append({"question_id":f"q_{cid}_{qn}","question":prompt,"expected_answer":explanation[:500] or f"Respuesta pendiente de validación para {title}.",
              "concept_id":cid,"required_concepts":[cid],"required_prerequisites":prereqs,"difficulty":"mixed","question_type":qtype,
              "source":"generated_from_corpus_structure","split":split,"gold_chunk_ids":gold,"gold_concept_ids":[cid],"gold_prerequisite_ids":prereqs,
              "provenance":{"question":"generated","expected_answer":"corpus" if explanation else "generated","gold_ids":"derived_from_alignment"}})
    return chunk_rows,concepts,units,questions,relations
