from __future__ import annotations
from time import perf_counter

from ai_tutor.graph.spreading_activation import spread_activation
from ai_tutor.planning import analyze_query, build_learning_path, optimize_context
from ai_tutor.student_model import get_student_profile
from .base import RetrievalResult, RetrievedChunk
from .graph_rag import GraphRAGRetriever


class PEPPlanRAGRetriever:
    """PEP-Plan-RAG v3: graph evidence + population signal + learner-aware planning."""

    name = "pep_plan_rag"

    def __init__(self, baseline, graph, concepts, instructional_units, config=None):
        self.baseline = baseline
        self.graph = graph
        self.config = config or {}
        self.concepts = {item["concept_id"]: item for item in concepts}
        self.concept_labels = {key: value.get("canonical_name", key) for key, value in self.concepts.items()}
        self.instructional_units = {item["concept_id"]: item for item in instructional_units}
        self.graph_retriever = GraphRAGRetriever(baseline, graph, self.config)

    @staticmethod
    def _normalize(values):
        maximum = max(values.values(), default=0.0)
        return {key: (value / maximum if maximum > 0 else 0.0) for key, value in values.items()}

    def retrieve(self, query: str, top_k: int = 5, **kwargs) -> RetrievalResult:
        started = perf_counter()
        pool_k = max(top_k * self.config.get("candidate_pool_multiplier", 3), 10)
        direct = self.baseline.retrieve(query, pool_k)
        graph_result = self.graph_retriever.retrieve(query, pool_k)
        targets = list(dict.fromkeys(direct.concepts))[:self.config.get("max_target_concepts", 5)]
        student = get_student_profile(kwargs.get("student_state", kwargs.get("student_profile", "unknown")))

        planning_started = perf_counter()
        analysis = analyze_query(query, targets, self.instructional_units)
        path = build_learning_path(
            self.graph, targets, student, self.concept_labels,
            max_depth=self.config.get("planning_max_depth", 3),
            max_nodes=self.config.get("planning_max_nodes", 24),
            mastery_threshold=self.config.get("mastery_threshold", 0.65),
        )
        planning_ms = (perf_counter() - planning_started) * 1000

        activation_started = perf_counter()
        seed_scores = {concept: 1.0 / (index + 1) for index, concept in enumerate(targets)}
        activation = spread_activation(self.graph, seed_scores, self.config)
        activation_ms = (perf_counter() - activation_started) * 1000

        candidates = {}
        direct_ids = set()
        direct_scores = {}
        for chunk in direct.chunks:
            candidates[chunk.chunk_id] = chunk; direct_ids.add(chunk.chunk_id); direct_scores[chunk.chunk_id] = chunk.score
        for chunk in graph_result.chunks:
            if chunk.chunk_id not in candidates:
                candidates[chunk.chunk_id] = RetrievedChunk(chunk.chunk_id, chunk.text, chunk.score, chunk.concept_ids, chunk.metadata)
        planned = set(path["ordered_concepts"])
        activated = set(activation.final)
        for concept in planned | activated:
            if concept not in self.graph:
                continue
            for _, node, data in self.graph.out_edges(concept, data=True):
                if data.get("edge_type") != "EXPLAINS" or not node.startswith("chunk::"):
                    continue
                chunk_id = node.split("::", 1)[1]
                raw = self.baseline.chunks.get(chunk_id)
                if raw and chunk_id not in candidates:
                    candidates[chunk_id] = RetrievedChunk(chunk_id, raw["text"], 0.0, raw.get("concept_ids", []), raw)

        direct_norm = self._normalize({cid: direct_scores.get(cid, 0.0) for cid in candidates})
        ppr = graph_result.debug_info.get("ppr_scores", {})
        ppr_norm = self._normalize({cid: sum(ppr.get(concept, 0.0) for concept in chunk.concept_ids)
                                    for cid, chunk in candidates.items()})
        activation_norm = self._normalize({cid: sum(activation.final.get(concept, 0.0) for concept in chunk.concept_ids)
                                           for cid, chunk in candidates.items()})
        # The pedagogical planner contributes learner-specific gaps, while the
        # graph retriever preserves prerequisites evidenced by bounded expansion.
        # Keeping both prevents a sparse learner model from erasing graph signal.
        graph_prerequisites = set(graph_result.debug_info.get("prerequisites_activated", []))
        missing = set(path["missing_prerequisites"])
        prerequisite_ids = missing | graph_prerequisites
        misconception_concepts = {item["concept_id"] for item in analysis["detected_misconceptions"]}
        instructional_types = {"definition", "explanation", "worked_example", "example"}
        weights = self.config.get("utility_weights", {})
        utility = {}; contributions = {}
        for chunk_id, chunk in candidates.items():
            target = float(any(cid in targets for cid in chunk.concept_ids))
            prerequisite = float(any(cid in prerequisite_ids for cid in chunk.concept_ids))
            gap = max((1.0 - path["mastery"].get(cid, student.default_mastery) for cid in chunk.concept_ids), default=0.0)
            misconception = float(any(cid in misconception_concepts for cid in chunk.concept_ids))
            instructional = float(chunk.metadata.get("chunk_type") in instructional_types)
            parts = {"direct": direct_norm[chunk_id], "ppr": ppr_norm[chunk_id], "target": target,
                     "prerequisite_need": prerequisite, "student_gap": gap, "misconception": misconception,
                     "instructional": instructional, "activation": activation_norm[chunk_id]}
            score = sum(float(weights.get(name, 0.0)) * value for name, value in parts.items())
            utility[chunk_id] = score; contributions[chunk_id] = {**parts, "utility": score}
            chunk.score = score
        ranked = sorted(candidates.values(), key=lambda chunk: (-utility[chunk.chunk_id], chunk.chunk_id))
        selection_started = perf_counter()
        selected, buckets = optimize_context(
            ranked, top_k, direct_ids, prerequisite_ids, utility,
            redundancy_weight=self.config.get("redundancy_weight", 0.12),
            min_direct=self.config.get("min_direct_evidence", 2),
            min_prerequisite=self.config.get("min_prerequisite_evidence", 1) if prerequisite_ids else 0,
            min_instructional=self.config.get("min_instructional_evidence", 1),
        )
        selection_ms = (perf_counter() - selection_started) * 1000
        latency = (perf_counter() - started) * 1000
        tutorial_plan = {
            "diagnose": analysis["query_type"],
            "activate_prior_knowledge": path["missing_prerequisites"][:3],
            "teach_targets": targets[:3],
            "micro_check": "Comprobar el prerrequisito de menor dominio antes de consolidar el concepto objetivo.",
        }
        debug = {
            "pep_version": "v3", "student_state": student.to_dict(), "query_analysis": analysis,
            "learning_path": path, "tutorial_plan": tutorial_plan,
            "initial_activation": seed_scores, "final_activation": activation.final,
            "activation_history": activation.history, "iterations": activation.iterations,
            "activated_concepts": list(activation.final), "prerequisites_activated": sorted(prerequisite_ids),
            "ppr_scores": ppr, "rerank_contributions": contributions, "context_buckets": buckets,
            "final_chunks": [chunk.chunk_id for chunk in selected], "nodes_visited": activation.nodes_visited,
            "edges_visited": activation.edges_visited, "planning_latency_ms": planning_ms,
            "population_dynamics_latency_ms": activation_ms, "reranking_latency_ms": selection_ms,
            "retrieval_latency_ms": latency,
        }
        concepts = list(dict.fromkeys(concept for chunk in selected for concept in chunk.concept_ids))
        return RetrievalResult(query, selected, concepts, [chunk.score for chunk in selected],
                               {"method": self.name, "student_profile": student.profile_id}, latency, debug)
