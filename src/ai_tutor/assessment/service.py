from __future__ import annotations
from .bank import build_micro_check
from .policy import decide
from .schema import MicroCheck
from .validators import evaluate


class AssessmentService:
    def __init__(self,repository,learning_service,concept_labels=None,concept_prerequisites=None):
        self.repository=repository; self.learning=learning_service
        self.labels=concept_labels or {}; self.prerequisites=concept_prerequisites or {}

    def create(self,concept_ids):
        concept_id=next(iter(concept_ids or []),"")
        if not concept_id: raise ValueError("Primero realiza una consulta para detectar un concepto")
        check=build_micro_check(concept_id,self.labels.get(concept_id,""))
        self.repository.save_micro_check(check.to_dict())
        return check

    def submit(self,user_id,conversation_id,check_data,answer):
        check=MicroCheck(**check_data)
        attempt=self.repository.next_attempt_number(user_id,check.micro_check_id)
        result=evaluate(check,answer)
        state=self.learning.state_for(user_id); before=state.mastery_for(check.concept_id)
        update=self.repository.add_learning_evidence(
            user_id,check.concept_id,"graded_micro_check",result.score,"automatic_validator",
            conversation_id,{"micro_check_id":check.micro_check_id,"answer":answer,"validator":check.validator},1.0)
        decision=decide(result,update["mastery"],attempt,self.prerequisites.get(check.concept_id,[]))
        hint=(check.hint_sequence[min(max(decision.hint_level,1),len(check.hint_sequence))-1]
              if decision.hint_level and check.hint_sequence else "")
        self.repository.save_assessment_attempt(user_id,conversation_id,check.micro_check_id,answer,
                                                result.to_dict(),decision.to_dict(),before,update["mastery"])
        return {"micro_check":check.to_dict(),"attempt_number":attempt,"evaluation":result.to_dict(),
                "decision":decision.to_dict(),"hint":hint,"mastery_before":before,
                "mastery_after":update["mastery"],"student_state":self.learning.state_for(user_id).to_dict()}
