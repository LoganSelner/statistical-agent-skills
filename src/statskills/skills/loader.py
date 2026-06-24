"""Progressive-disclosure rendering (ROADMAP §5).

Renders the exact context payload a skill (or library) contributes at a resolution level
— the ablation surface SkillsBench found mattered most. L0 = name + description; L1 adds
the instructions body; L2 adds inline examples; L3 adds the bundled resource contents.
The loader is the single place that decides what enters the context window per level.
"""

from __future__ import annotations

from collections.abc import Iterable

from statskills.skills.schema import Skill, SkillResolution


def render(skill: Skill, level: SkillResolution) -> str:
    """The context payload one skill contributes at ``level`` (cumulative L0→L3)."""
    parts = [f"## {skill.name}\n{skill.description}"]
    if level >= SkillResolution.L1 and skill.body:
        parts.append(skill.body)
    if level >= SkillResolution.L2 and skill.examples:
        blocks = "\n\n".join(f"```python\n{ex}\n```" for ex in skill.examples)
        parts.append(f"### Examples\n{blocks}")
    if level >= SkillResolution.L3 and skill.resources:
        rendered = []
        for resource in skill.resources:
            content = (skill.path / resource.relative_path).read_text()
            rendered.append(f"#### {resource.relative_path}\n```\n{content}```")
        parts.append("### Bundled resources\n" + "\n\n".join(rendered))
    return "\n\n".join(parts)


def render_library(skills: Iterable[Skill], level: SkillResolution) -> str:
    """The combined payload for a set of skills, deterministically ordered by name."""
    ordered = sorted(skills, key=lambda s: s.name)
    return "\n\n".join(render(s, level) for s in ordered)


def render_discovery(skills: Iterable[Skill]) -> str:
    """The L0 discovery surface — each skill's name + description, one per line.

    This is what an agent sees in agent-activated delivery: just enough to decide which
    skill to read (the body loads only when the agent opens its file), deterministically
    ordered by name.
    """
    ordered = sorted(skills, key=lambda s: s.name)
    return "\n".join(f"- {s.name}: {s.description}" for s in ordered)
