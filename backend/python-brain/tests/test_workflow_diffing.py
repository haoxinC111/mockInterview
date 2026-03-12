from app.workflows.diffing import diff_report_results, diff_resume_results, diff_turn_results


def test_diff_turn_results_highlights_contract_drift() -> None:
    diff = diff_turn_results({"next_action": "end", "turn_eval": {}}, {"next_action": "next_topic", "turn_eval": {}})
    assert "next_action" in diff


def test_diff_report_results_highlights_score_changes() -> None:
    diff = diff_report_results(
        {"overall_score": 6.0, "dimension_scores": {"technical_depth": 6}},
        {"overall_score": 7.0, "dimension_scores": {"technical_depth": 7}},
    )
    assert "overall_score" in diff
    assert "dimension_scores" in diff


def test_diff_resume_results_highlights_profile_changes() -> None:
    diff = diff_resume_results(
        {"resume_text": "abc", "parsed_profile": {"skills": ["python"]}},
        {"resume_text": "abcdef", "parsed_profile": {"skills": ["python", "langgraph"]}},
    )
    assert "resume_text" in diff
    assert "parsed_profile" in diff
