from __future__ import annotations
import ast
import math
import operator
import re
import unicodedata

from .schema import AssessmentResult, MicroCheck


_OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,
      ast.Pow:operator.pow,ast.USub:operator.neg,ast.UAdd:operator.pos}


def _plain(value):
    value=unicodedata.normalize("NFKD",str(value).lower())
    return " ".join("".join(ch for ch in value if not unicodedata.combining(ch)).split())


def _numeric_expression(text):
    cleaned=_plain(text).replace("^","**").replace(",",".")
    cleaned=re.sub(r"^[a-z]\s*=\s*","",cleaned)
    node=ast.parse(cleaned,mode="eval").body
    def visit(item):
        if isinstance(item,ast.Constant) and isinstance(item.value,(int,float)): return float(item.value)
        if isinstance(item,ast.BinOp) and type(item.op) in _OPS:return _OPS[type(item.op)](visit(item.left),visit(item.right))
        if isinstance(item,ast.UnaryOp) and type(item.op) in _OPS:return _OPS[type(item.op)](visit(item.operand))
        raise ValueError("unsupported numeric expression")
    return visit(node)


def evaluate(check: MicroCheck, answer: str) -> AssessmentResult:
    normalized=_plain(answer)
    if check.validator=="numeric_equivalence":
        try:
            observed=_numeric_expression(answer); expected=_numeric_expression(check.expected_answer)
            correct=math.isclose(observed,expected,rel_tol=check.tolerance,abs_tol=check.tolerance)
        except (ValueError,SyntaxError,ZeroDivisionError,OverflowError): correct=False
        score=1.0 if correct else 0.0
    elif check.validator=="choice":
        correct=normalized.strip(" .)")==_plain(check.expected_answer).strip(" .)")
        score=1.0 if correct else 0.0
    elif check.validator=="keyword_rubric":
        keywords=[item.strip() for item in _plain(check.expected_answer).split("|") if item.strip()]
        matches=sum(keyword in normalized for keyword in keywords)
        score=matches/max(1,len(keywords)); correct=score>=.75
    else:
        correct=normalized==_plain(check.expected_answer); score=1.0 if correct else 0.0
    feedback=("Correcto. La respuesta satisface el criterio del micro-check."
              if correct else "Todavía no cumple el criterio. Revisemos una pista antes del siguiente intento.")
    return AssessmentResult(correct,score,normalized,feedback,check.validator)
