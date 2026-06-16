"""Tests for the CodeAct action parser."""

from __future__ import annotations

from statskills.agent.action import CodeAction, FinalAnswer, parse_action


def test_parses_python_code_block():
    action = parse_action("Let me compute it.\n```python\nprint(2 + 2)\n```")
    assert isinstance(action, CodeAction)
    assert action.code == "print(2 + 2)"


def test_parses_bare_fence_without_language():
    action = parse_action("```\nx = 1\nprint(x)\n```")
    assert isinstance(action, CodeAction)
    assert action.code == "x = 1\nprint(x)"


def test_final_answer_marker():
    action = parse_action("The mean is 3.5.\nFINAL ANSWER: 3.5")
    assert isinstance(action, FinalAnswer)
    assert action.answer == "3.5"


def test_final_answer_is_case_insensitive_and_multiline():
    action = parse_action("final answer: line1\nline2")
    assert isinstance(action, FinalAnswer)
    assert action.answer == "line1\nline2"


def test_code_runs_before_a_placeholder_final_answer():
    # Models often pre-write a placeholder answer alongside the code they intend to
    # run; the harness must run the code, not finalize on the placeholder.
    action = parse_action(
        "```python\nprint(df['x'].mean())\n```\nFINAL ANSWER: [the mean]"
    )
    assert isinstance(action, CodeAction)
    assert action.code == "print(df['x'].mean())"


def test_first_nonempty_code_block_used():
    action = parse_action("```python\n\n```\n```python\nprint('real')\n```")
    assert isinstance(action, CodeAction)
    assert action.code == "print('real')"


def test_no_actionable_content_returns_none():
    assert parse_action("I'm still thinking about the approach.") is None
