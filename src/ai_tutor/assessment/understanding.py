from __future__ import annotations
import re
import unicodedata


class UnderstandingEvaluator:
    """Auditable heuristic evaluator, independent from self-report buttons."""

    @staticmethod
    def _plain(text):
        value=unicodedata.normalize("NFKD",(text or "").lower())
        return " ".join("".join(ch for ch in value if not unicodedata.combining(ch)).split())

    def evaluate(self,message,previous_tutor_message="",concept_ids=None,concept_labels=None):
        text=self._plain(message); concept_ids=list(concept_ids or [])
        labels=concept_labels or {}; features={"length":len(text),"has_equation":bool(re.search(r"[=^²√]|\d",text))}
        confusion=any(term in text for term in ("no entiendo","no entendi","estoy perdido","me confundi","no se como"))
        uncertainty=any(term in text for term in ("creo que","no estoy seguro","mas o menos","tal vez"))
        explanation_markers=sum(term in text for term in ("porque","entonces","por lo tanto","primero","despues","significa"))
        concept_terms=[]
        for concept_id in concept_ids:
            label=self._plain(labels.get(concept_id,concept_id.replace("_"," ")))
            concept_terms.extend(token for token in label.split() if len(token)>4)
        overlap=sum(term in text for term in set(concept_terms)); features.update({"confusion":confusion,"uncertainty":uncertainty,"explanation_markers":explanation_markers,"concept_overlap":overlap})
        if confusion:return self._result("not_understood",.15,.85,features,"explicit_confusion")
        if uncertainty:return self._result("partial",.50,.65,features,"uncertainty_language")
        if len(text)>=35 and (explanation_markers>=1 or overlap>=1):
            score=min(.9,.60+.08*explanation_markers+.05*overlap)
            return self._result("understood" if score>=.75 else "partial",score,.60,features,"explanation_quality")
        if "?" in previous_tutor_message and text:
            return self._result("unscored",None,.30,features,"answer_without_gold")
        return self._result("unknown",None,.10,features,"insufficient_evidence")

    @staticmethod
    def _result(classification,score,confidence,features,reason):
        return {"classification":classification,"score":score,"confidence":confidence,
                "features":features,"reason":reason,"changes_mastery":score is not None and confidence>=.60}
