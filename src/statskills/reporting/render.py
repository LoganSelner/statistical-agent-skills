"""Render a :class:`Report` as shareable Markdown with inline source indices (§10).

Each quantitative result shows the trajectory step that produced it (``[step N]``); a
result whose number could not be traced to that step is marked unverified, so a reader
sees exactly which figures are grounded. Pure/stdlib — the structured ``Report`` is the
machine-readable artifact, this is the human-readable one.
"""

from __future__ import annotations

from statskills.reporting.schema import Report

_UNVERIFIED = " — **[unverified: not found in the cited step]**"


def render_markdown(report: Report) -> str:
    """Render ``report`` as Markdown; verify the report first to populate the flags."""
    lines = [
        f"# Statistical report — {report.task_id}",
        "",
        "## Question",
        report.question,
        "",
        "## Data",
        report.data_summary,
        "",
        "## Method",
        report.method,
        "",
        "## Assumption checks",
        report.assumption_checks,
        "",
        "## Results",
    ]
    if report.results:
        for claim in report.results:
            flag = _UNVERIFIED if claim.verified is False else ""
            lines.append(
                f"- **{claim.label}:** {claim.value} _[step {claim.step}]_{flag}"
            )
    else:
        lines.append("_(no quantitative results)_")
    lines += [
        "",
        "## Interpretation",
        report.interpretation,
        "",
        "## Caveats",
        report.caveats,
    ]
    flagged = sum(1 for c in report.results if c.verified is False)
    if flagged:
        lines += [
            "",
            "---",
            f"> **Warning:** {flagged} result(s) could not be traced to the cited "
            "step's output — treat as unverified.",
        ]
    return "\n".join(lines)
