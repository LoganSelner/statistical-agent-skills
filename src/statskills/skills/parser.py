"""Parse an Anthropic Agent-Skills ``SKILL.md`` folder into a :class:`Skill` (§5).

Splits YAML frontmatter from the markdown body, validates the open-standard frontmatter
(``name`` ≤64 chars of ``[a-z0-9-]``, ``description`` non-empty ≤1024), lifts the
``## Examples`` section's code blocks into the L2 payload, and discovers bundled
``scripts/``/``references/`` resources (L3). We stay on the open standard so authored
skills remain portable and comparable to the ecosystem.
"""

from __future__ import annotations

from pathlib import Path
import re

import yaml

from statskills.skills.schema import Skill, SkillResource

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n?(.*)\Z", re.DOTALL)
_NAME = re.compile(r"^[a-z0-9-]+$")
_EXAMPLES_HEADING = re.compile(r"^##\s+Examples\s*$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^##\s+\S", re.MULTILINE)
_CODE_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


class SkillError(ValueError):
    """A SKILL.md that violates the Agent-Skills standard or our conventions."""


def parse_skill(path: Path) -> Skill:
    """Parse a skill folder (or its SKILL.md) into a :class:`Skill`."""
    skill_md = path / "SKILL.md" if path.is_dir() else path
    if not skill_md.is_file():
        raise SkillError(f"No SKILL.md at {skill_md}")

    match = _FRONTMATTER.match(skill_md.read_text())
    if not match:
        raise SkillError(f"{skill_md}: missing or malformed YAML frontmatter")
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as e:
        raise SkillError(f"{skill_md}: invalid frontmatter YAML: {e}") from e
    if not isinstance(meta, dict):
        raise SkillError(f"{skill_md}: frontmatter must be a mapping")

    name = str(meta.get("name", "")).strip()
    description = str(meta.get("description", "")).strip()
    _validate(skill_md, name, description)

    body, examples = _split_examples(match.group(2).strip())
    return Skill(
        name=name,
        description=description,
        body=body,
        examples=examples,
        resources=_discover_resources(skill_md.parent),
        path=skill_md.parent,
    )


def _validate(skill_md: Path, name: str, description: str) -> None:
    if not name:
        raise SkillError(f"{skill_md}: frontmatter 'name' is required")
    if len(name) > 64 or not _NAME.match(name):
        raise SkillError(
            f"{skill_md}: 'name' must be ≤64 chars of [a-z0-9-]; got {name!r}"
        )
    if not description:
        raise SkillError(f"{skill_md}: frontmatter 'description' is required")
    if len(description) > 1024:
        raise SkillError(f"{skill_md}: 'description' must be ≤1024 chars")


def _split_examples(body: str) -> tuple[str, tuple[str, ...]]:
    """Lift the ``## Examples`` section's code blocks out of the body (L2).

    Returns the instructions (body with the Examples section removed) and the fenced
    code blocks from that section. Bounded at the next ``##`` heading so a later section
    is preserved in the instructions, not swallowed.
    """
    heading = _EXAMPLES_HEADING.search(body)
    if not heading:
        return body, ()
    before, rest = body[: heading.start()], body[heading.end() :]
    following = _NEXT_HEADING.search(rest)
    section, after = (
        (rest[: following.start()], rest[following.start() :])
        if following
        else (rest, "")
    )
    examples = tuple(b.strip() for b in _CODE_BLOCK.findall(section) if b.strip())
    instructions = before.rstrip()
    if after.strip():
        instructions = f"{instructions}\n\n{after.strip()}"
    return instructions.strip(), examples


def _discover_resources(skill_dir: Path) -> tuple[SkillResource, ...]:
    resources: list[SkillResource] = []
    for subdir, kind in (("scripts", "script"), ("references", "reference")):
        root = skill_dir / subdir
        if root.is_dir():
            resources += [
                SkillResource(f.relative_to(skill_dir).as_posix(), kind)
                for f in sorted(root.rglob("*"))
                if f.is_file()
            ]
    return tuple(resources)
