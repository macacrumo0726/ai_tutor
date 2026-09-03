from ai_tutor.instructional.comprehensive_builder import build_database

def test_comprehensive_builder_grounds_toc_and_completes_units():
    toc=[
      [2,"CAPÍTULO 1 FUNDAMENTOS",1],
      [3,"1.1 NÚMEROS REALES",1],
      [4,"Propiedades de los números reales",1],
      [4,"1.1 Ejercicios",2],
      [3,"1.2 ECUACIONES",3],
      [4,"Ecuaciones lineales",3],
    ]
    pages=["Definición de números reales. EJEMPLO 1 sumar dos números reales. "*20,
           "EJERCICIOS conceptuales sobre números reales. "*20,
           "Una ecuación lineal contiene una incógnita. "*20]
    chunks,concepts,units,questions,relations=build_database(toc,pages,[])
    assert len(concepts)==4
    assert all(c["source_chunks"] for c in concepts)
    assert all(u["worked_example"] and u["solution"] for u in units)
    assert len(questions)==3*len(concepts)
    assert {r["edge_type"] for r in relations}=={"NEXT_CONCEPT","PREREQUISITE_OF"}
