from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .auth import AuthorizationError, RevisionConflict
from .models import (
    ComparisonSnapshot,
    Experiment,
    Hypothesis,
    HypothesisRelation,
    ProjectReflection,
    User,
)
from .services import get_project

METHODS = {"prototype_walkthrough", "user_interview", "comparative_usability_test", "model_output_evaluation", "technical_feasibility_test", "cost_estimate_simulation", "pilot", "other"}
STATUSES = {"planned", "in_progress", "completed", "cancelled"}
DECISIONS = {"continue", "revise", "retest", "stop", "undecided"}


def list_experiments(db: Session, actor: User, project_id: UUID) -> list[Experiment]:
    get_project(db, actor, project_id)
    return list(db.scalars(select(Experiment).where(Experiment.project_id == project_id).order_by(Experiment.created_at)))


def create_experiment(db: Session, actor: User, project_id: UUID, primary_hypothesis_id: UUID, title: str, method: str) -> Experiment:
    get_project(db, actor, project_id)
    hypothesis = db.get(Hypothesis, primary_hypothesis_id)
    if hypothesis is None or hypothesis.project_id != project_id:
        raise AuthorizationError("Primary hypothesis must belong to this project")
    if not title.strip() or method not in METHODS:
        raise ValueError("An experiment requires a title and valid method")
    experiment = Experiment(project_id=project_id, primary_hypothesis_id=primary_hypothesis_id, title=title.strip(), method=method)
    db.add(experiment)
    db.commit()
    return experiment


def update_experiment(db: Session, actor: User, experiment_id: UUID, revision: int, **fields) -> Experiment:
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise AuthorizationError("Experiment not found")
    get_project(db, actor, experiment.project_id)
    allowed = {"title", "method", "procedure", "participants", "comparison_baseline", "metric", "success_criterion", "guardrail", "resources", "owner", "planned_date", "status", "results", "evidence_links", "limitations", "conclusion", "resulting_decision"}
    for key, value in fields.items():
        if key in allowed:
            setattr(experiment, key, value.strip() if isinstance(value, str) else value)
    if experiment.method not in METHODS or experiment.status not in STATUSES or experiment.resulting_decision not in DECISIONS:
        raise ValueError("Invalid experiment method, status, or decision")
    if experiment.revision != revision:
        raise RevisionConflict("The experiment changed since it was loaded")
    experiment.revision += 1
    db.commit()
    return experiment


def save_reflection(db: Session, actor: User, project_id: UUID, reflection_type: str, content: str, **fields) -> ProjectReflection:
    get_project(db, actor, project_id)
    if reflection_type not in {"adversarial_risk", "feedback_loop"}:
        raise ValueError("Invalid reflection type")
    reflection = db.scalar(select(ProjectReflection).where(ProjectReflection.project_id == project_id, ProjectReflection.reflection_type == reflection_type))
    if reflection is None:
        reflection = ProjectReflection(project_id=project_id, reflection_type=reflection_type, revision=1)
        db.add(reflection)
    reflection.content = content
    if reflection_type == "adversarial_risk" and fields.get("subjective_score") is not None:
        score = fields["subjective_score"]
        if not 0 <= score <= 5:
            raise ValueError("Risk discussion score must be between 0 and 5")
        reflection.subjective_score = score
    allowed = {"attack_entry_point", "unwanted_behavior", "affected_data_action", "consequence", "proposed_safeguard", "signal_to_collect", "signal_meaning", "possible_product_change", "human_interpretation_needed", "evaluation_after_change"}
    for key, value in fields.items():
        if key in allowed:
            setattr(reflection, key, value or "")
    reflection.revision += 1
    db.commit()
    return reflection


def completion_checklist(db: Session, actor: User, project_id: UUID) -> dict[str, bool]:
    project = get_project(db, actor, project_id)
    main = db.scalar(select(Hypothesis).where(Hypothesis.project_id == project_id, Hypothesis.kind == "main"))
    estimates = list(getattr(project, "dimension_estimates", []))
    experiments = list_experiments(db, actor, project_id)
    supporting = list(db.scalars(select(Hypothesis).where(Hypothesis.project_id == project_id, Hypothesis.kind == "supporting")))
    main_id = main.id if main else None
    relations = list(db.scalars(select(HypothesisRelation).where(HypothesisRelation.project_id == project_id, HypothesisRelation.relation_type == "contributes_to")))
    graph = {}
    for relation in relations:
        graph.setdefault(relation.from_hypothesis_id, set()).add(relation.to_hypothesis_id)
    connected = False
    for item in supporting:
        stack = [item.id]
        visited = set()
        while stack:
            current = stack.pop()
            if current == main_id:
                connected = True
                break
            if current not in visited:
                visited.add(current)
                stack.extend(graph.get(current, ()))
        if connected:
            break
    snapshots = db.scalar(select(ComparisonSnapshot.id).where(ComparisonSnapshot.project_id == project_id).limit(1))
    return {
        "Project brief complete": bool(project.product_name and project.short_description and project.target_user and project.job_to_be_done and project.current_problem and main and main.statement),
        "5/5 dimensions assessed or marked unknown": len(estimates) == 5 and all(item.status in {"estimated", "unknown"} for item in estimates),
        "Comparator selected": snapshots is not None,
        "2 supporting hypotheses created": len(supporting) >= 2,
        "Hypotheses connected to value": connected,
        "Priority hypothesis selected": any(item.primary_hypothesis_id in {hypothesis.id for hypothesis in supporting} for item in experiments),
        "Next experiment defined": any(item.status == "planned" for item in experiments),
    }


def priority_guidance(db: Session, actor: User, project_id: UUID) -> str:
    get_project(db, actor, project_id)
    hypotheses = list(db.scalars(select(Hypothesis).where(Hypothesis.project_id == project_id, Hypothesis.kind == "supporting").order_by(Hypothesis.impact_if_wrong, Hypothesis.evidence_strength)))
    if not hypotheses:
        return "No supporting hypotheses yet. Unknown impact or evidence stays outside the scored priority matrix."
    scored = [item for item in hypotheses if item.impact_if_wrong != "unknown" and item.evidence_strength != "unknown"]
    needs_assessment = [item for item in hypotheses if item not in scored]
    lines = ["Evidence-versus-impact priority matrix", "Higher impact and lower evidence indicate uncertainty worth investigating."]
    if scored:
        lines.append("Scored hypotheses:")
        for item in scored:
            lines.append(f"- Impact {item.impact_if_wrong} / Evidence {item.evidence_strength}: {item.statement}")
    else:
        lines.append("Scored hypotheses: none")
    lines.append("Needs assessment (not placed on the matrix):")
    for item in needs_assessment:
        lines.append(f"- {item.statement} [impact={item.impact_if_wrong}, evidence={item.evidence_strength}]")
    return "\n".join(lines)
