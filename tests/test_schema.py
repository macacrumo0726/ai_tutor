import pytest
from ai_tutor.instructional.schema import Concept

def test_concept_schema_validates_provenance():
    c=Concept("x","X","x","d","t","s","easy","learn",provenance={"description":"corpus"}); c.validate()
    c.provenance={"description":"unknown"}
    with pytest.raises(ValueError): c.validate()

def test_built_database_has_no_empty_required_instructional_fields():
    import json
    from pathlib import Path
    path=Path("data/instructional/instructional_units.jsonl")
    if not path.exists(): pytest.skip("dataset not built")
    units=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    required=["learning_objective","concept_explanation","worked_example","guided_example","common_misconceptions","diagnostic_question","practice_question","hint_level_1","hint_level_2","hint_level_3","solution"]
    assert units and all(all(unit.get(field) for field in required) for unit in units)
