from __future__ import annotations

from langgraph.graph import StateGraph

from services.brain_agent.nodes import (
    BrainState,
    action_generation_node,
    decision_node,
    extract_data_node,
    parse_summary_node,
    questionnaire_generation_node,
    response_analysis_node,
    risk_evaluation_node,
)

# ---------------------------------------------------------------------------
# Intake graph: discharge summary -> full clinical pipeline
# ---------------------------------------------------------------------------

_intake = StateGraph(BrainState)

_intake.add_node("parse_summary", parse_summary_node)
_intake.add_node("extract_data", extract_data_node)
_intake.add_node("risk_evaluation", risk_evaluation_node)
_intake.add_node("questionnaire_generation", questionnaire_generation_node)
_intake.add_node("decision", decision_node)
_intake.add_node("action_generation", action_generation_node)

_intake.set_entry_point("parse_summary")
_intake.add_edge("parse_summary", "extract_data")
_intake.add_edge("extract_data", "risk_evaluation")
_intake.add_edge("risk_evaluation", "questionnaire_generation")
_intake.add_edge("questionnaire_generation", "decision")
_intake.add_edge("decision", "action_generation")
_intake.set_finish_point("action_generation")

intake_chain = _intake.compile()

# ---------------------------------------------------------------------------
# Response graph: patient responses -> analysis -> decision -> actions
# ---------------------------------------------------------------------------

_response = StateGraph(BrainState)

_response.add_node("response_analysis", response_analysis_node)
_response.add_node("decision", decision_node)
_response.add_node("action_generation", action_generation_node)

_response.set_entry_point("response_analysis")
_response.add_edge("response_analysis", "decision")
_response.add_edge("decision", "action_generation")
_response.set_finish_point("action_generation")

response_chain = _response.compile()
