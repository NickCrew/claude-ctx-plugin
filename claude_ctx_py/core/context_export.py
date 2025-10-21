"""Context export functionality for claude-ctx.

This module provides functionality for exporting the current claude-ctx context
as a single markdown file with optional component selection.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

from .base import _resolve_claude_dir, _iter_md_files, _parse_active_entries, _color, GREEN, YELLOW, RED


def _read_file_content(file_path: Path) -> str:
    """Read file content safely.

    Args:
        file_path: Path to file to read

    Returns:
        File content as string, or error message if read fails
    """
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"<!-- Error reading file: {e} -->"


def _get_core_framework_files(claude_dir: Path) -> Dict[str, Path]:
    """Get core framework files (FLAGS.md, PRINCIPLES.md, RULES.md).

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary mapping file names to their paths
    """
    core_files = {}
    for name in ["FLAGS.md", "PRINCIPLES.md", "RULES.md"]:
        path = claude_dir / name
        if path.exists():
            core_files[name] = path
    return core_files


def _get_active_rules(claude_dir: Path) -> Dict[str, Path]:
    """Get active rule files from rules/ directory.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary mapping rule names to their paths
    """
    rules_dir = claude_dir / "rules"
    if not rules_dir.exists():
        return {}

    # Parse CLAUDE.md to find active rules
    claude_md = claude_dir / "CLAUDE.md"
    active_rules = set()

    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("@rules/") and line.endswith(".md"):
                rule_name = line[7:]  # Remove "@rules/"
                active_rules.add(rule_name)

    # Get all rule files
    rule_files = {}
    for rule_file in rules_dir.glob("*.md"):
        if rule_file.name in active_rules or not active_rules:
            rule_files[f"rules/{rule_file.name}"] = rule_file

    return rule_files


def _get_active_modes(claude_dir: Path) -> Dict[str, Path]:
    """Get active mode files from modes/ directory.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary mapping mode names to their paths
    """
    modes_dir = claude_dir / "modes"
    if not modes_dir.exists():
        return {}

    # Parse CLAUDE.md to find active modes section
    claude_md = claude_dir / "CLAUDE.md"
    active_modes = set()

    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        in_active_section = False

        for line in content.splitlines():
            line = line.strip()
            if "# Active Behavioral Modes" in line:
                in_active_section = True
                continue
            elif line.startswith("# "):
                in_active_section = False

            if in_active_section and line.startswith("@modes/"):
                mode_name = line[7:]  # Remove "@modes/"
                active_modes.add(mode_name)

    # Get active mode files
    mode_files = {}
    for mode_file in modes_dir.glob("*.md"):
        if mode_file.name in active_modes:
            mode_files[f"modes/{mode_file.name}"] = mode_file

    return mode_files


def _get_active_agents(claude_dir: Path) -> Dict[str, Path]:
    """Get active agent files from agents/ directory.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary mapping agent names to their paths
    """
    agents_dir = claude_dir / "agents"
    if not agents_dir.exists():
        return {}

    agent_files = {}
    for agent_file in agents_dir.glob("*.md"):
        agent_files[f"agents/{agent_file.name}"] = agent_file

    return agent_files


def _get_mcp_docs(claude_dir: Path) -> Dict[str, Path]:
    """Get MCP documentation files from mcp/docs/ directory.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary mapping MCP doc names to their paths
    """
    mcp_docs_dir = claude_dir / "mcp" / "docs"
    if not mcp_docs_dir.exists():
        return {}

    # Parse CLAUDE.md to find active MCP docs
    claude_md = claude_dir / "CLAUDE.md"
    active_mcp_docs = set()

    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("@mcp/docs/") and line.endswith(".md"):
                doc_name = line[10:]  # Remove "@mcp/docs/"
                active_mcp_docs.add(doc_name)

    # Get MCP doc files
    mcp_files = {}
    for mcp_file in mcp_docs_dir.glob("*.md"):
        if mcp_file.name in active_mcp_docs or not active_mcp_docs:
            mcp_files[f"mcp/docs/{mcp_file.name}"] = mcp_file

    return mcp_files


def _get_skills(claude_dir: Path) -> Dict[str, Path]:
    """Get skill files from skills/ directory.

    Args:
        claude_dir: Path to .claude directory

    Returns:
        Dictionary mapping skill names to their paths
    """
    skills_dir = claude_dir / "skills"
    if not skills_dir.exists():
        return {}

    skill_files = {}
    for skill_file in skills_dir.glob("*.md"):
        skill_files[f"skills/{skill_file.name}"] = skill_file

    return skill_files


def collect_context_components(claude_dir: Path | None = None) -> Dict[str, Dict[str, Path]]:
    """Collect all context components organized by category.

    Args:
        claude_dir: Path to .claude directory (auto-detected if None)

    Returns:
        Dictionary mapping category names to dictionaries of component files
    """
    if claude_dir is None:
        claude_dir = _resolve_claude_dir()

    components = {
        "core": _get_core_framework_files(claude_dir),
        "rules": _get_active_rules(claude_dir),
        "modes": _get_active_modes(claude_dir),
        "agents": _get_active_agents(claude_dir),
        "mcp_docs": _get_mcp_docs(claude_dir),
        "skills": _get_skills(claude_dir),
    }

    return components


def export_context(
    output_path: Path | str,
    exclude_categories: Set[str] | None = None,
    exclude_files: Set[str] | None = None,
    claude_dir: Path | None = None,
    agent_generic: bool = True,
) -> Tuple[int, str]:
    """Export current claude-ctx context to a markdown file or stdout.

    Args:
        output_path: Path where to write the exported context, or "-" for stdout
        exclude_categories: Set of category names to exclude (core, rules, modes, agents, mcp_docs, skills)
        exclude_files: Set of specific file paths to exclude (e.g., "rules/quality-rules.md")
        claude_dir: Path to .claude directory (auto-detected if None)
        agent_generic: If True, use agent-generic format (default: True)

    Returns:
        Tuple of (exit_code, message)
    """
    if exclude_categories is None:
        exclude_categories = set()
    if exclude_files is None:
        exclude_files = set()

    if claude_dir is None:
        claude_dir = _resolve_claude_dir()

    # Collect components
    components = collect_context_components(claude_dir)

    # Build export content
    lines = []

    # Add header
    if agent_generic:
        lines.append("# AI Agent Context Export")
        lines.append("")
        lines.append("This file contains the complete context configuration for AI agent interactions.")
        lines.append(f"Exported from: {claude_dir}")
        lines.append("")
        lines.append("---")
        lines.append("")
    else:
        lines.append("# Claude CTX Context Export")
        lines.append("")
        lines.append(f"Exported from: {claude_dir}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Track what we've exported
    exported_count = 0
    skipped_count = 0

    # Category order and titles
    category_info = {
        "core": ("Core Framework", "Core behavioral configuration files"),
        "rules": ("Rules", "Active rule modules for workflow guidance"),
        "modes": ("Active Modes", "Currently active behavioral modes"),
        "agents": ("Active Agents", "Currently active specialized agents"),
        "mcp_docs": ("MCP Documentation", "Model Context Protocol integration documentation"),
        "skills": ("Skills", "Available skill definitions"),
    }

    for category, (title, description) in category_info.items():
        if category in exclude_categories:
            skipped_count += len(components.get(category, {}))
            continue

        files = components.get(category, {})
        if not files:
            continue

        # Add category header
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"*{description}*")
        lines.append("")

        # Add each file in the category
        for file_key, file_path in sorted(files.items()):
            if file_key in exclude_files:
                skipped_count += 1
                continue

            lines.append(f"### {file_key}")
            lines.append("")
            lines.append("```markdown")
            lines.append(_read_file_content(file_path))
            lines.append("```")
            lines.append("")
            exported_count += 1

    # Write output
    try:
        output_content = "\n".join(lines)

        # Check if output to stdout
        if str(output_path) == "-":
            sys.stdout.write(output_content)
            if not output_content.endswith("\n"):
                sys.stdout.write("\n")

            # Write status to stderr so it doesn't pollute stdout
            message = (
                f"{_color('✓', GREEN)} Context exported to stdout\n"
                f"  Exported: {exported_count} files\n"
                f"  Skipped: {skipped_count} files"
            )
            sys.stderr.write(message + "\n")
            return 0, ""  # Return empty message since we already wrote to stderr
        else:
            # Write to file
            if isinstance(output_path, str):
                output_path = Path(output_path)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output_content, encoding="utf-8")

            message = (
                f"{_color('✓', GREEN)} Context exported successfully\n"
                f"  Output: {output_path}\n"
                f"  Exported: {exported_count} files\n"
                f"  Skipped: {skipped_count} files"
            )
            return 0, message

    except Exception as e:
        return 1, f"{_color('✗', RED)} Failed to export context: {e}"


def list_context_components(claude_dir: Path | None = None) -> str:
    """List all available context components.

    Args:
        claude_dir: Path to .claude directory (auto-detected if None)

    Returns:
        Formatted string listing all components
    """
    if claude_dir is None:
        claude_dir = _resolve_claude_dir()

    components = collect_context_components(claude_dir)

    lines = ["Available context components:", ""]

    category_names = {
        "core": "Core Framework",
        "rules": "Rules",
        "modes": "Active Modes",
        "agents": "Active Agents",
        "mcp_docs": "MCP Documentation",
        "skills": "Skills",
    }

    for category, title in category_names.items():
        files = components.get(category, {})
        if not files:
            continue

        lines.append(f"{_color(title, GREEN)} ({len(files)} files)")
        for file_key in sorted(files.keys()):
            lines.append(f"  - {file_key}")
        lines.append("")

    return "\n".join(lines)
