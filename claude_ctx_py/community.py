"""Community contribution functions for claude-ctx.

This module provides functions for validating, installing, rating, and searching
community-contributed skills. It handles skill metadata validation, community
skill discovery, and installation workflows.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def validate_contribution(skill_path: Path) -> Tuple[bool, List[str]]:
    """Validate a community skill contribution.

    Validates that a skill file meets all requirements for community contribution:
    - Has valid YAML frontmatter with required fields
    - Name is in hyphen-case format
    - Description is under 1024 characters
    - Version follows semver format
    - License is Apache-2.0
    - Has 1-10 tags
    - Contains required sections
    - Token budget is between 800-5000

    Args:
        skill_path: Path to the skill file to validate

    Returns:
        Tuple of (is_valid, errors) where is_valid is True if validation passes
        and errors is a list of validation error messages

    Example:
        >>> valid, errors = validate_contribution(Path("skill.md"))
        >>> if not valid:
        ...     for error in errors:
        ...         print(f"Error: {error}")
    """
    if yaml is None:
        return False, ["PyYAML is required for validation. Install with: pip install pyyaml"]

    errors: List[str] = []

    # Check file exists
    if not skill_path.exists():
        return False, [f"File not found: {skill_path}"]

    # Read file content
    try:
        content = skill_path.read_text(encoding="utf-8")
    except Exception as e:
        return False, [f"Failed to read file: {e}"]

    # Extract frontmatter
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not frontmatter_match:
        errors.append("Missing YAML frontmatter (must start with --- and end with ---)")
        return False, errors

    frontmatter_text = frontmatter_match.group(1)

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError as e:
        errors.append(f"Invalid YAML frontmatter: {e}")
        return False, errors

    if not isinstance(frontmatter, dict):
        errors.append("Frontmatter must be a YAML dictionary")
        return False, errors

    # Validate required fields
    required_fields = ['name', 'version', 'author', 'license', 'description']
    for field in required_fields:
        if field not in frontmatter:
            errors.append(f"Missing required field: {field}")

    # Validate name format (hyphen-case)
    if 'name' in frontmatter:
        name = frontmatter['name']
        if not isinstance(name, str):
            errors.append("Field 'name' must be a string")
        elif not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
            errors.append(
                f"Field 'name' must be in hyphen-case format (lowercase letters, "
                f"numbers, and hyphens only): got '{name}'"
            )

    # Validate description length
    if 'description' in frontmatter:
        description = frontmatter['description']
        if not isinstance(description, str):
            errors.append("Field 'description' must be a string")
        elif len(description) >= 1024:
            errors.append(
                f"Field 'description' must be less than 1024 characters: "
                f"got {len(description)} characters"
            )

    # Validate version format (semver)
    if 'version' in frontmatter:
        version = frontmatter['version']
        if not isinstance(version, str):
            errors.append("Field 'version' must be a string")
        elif not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$', version):
            errors.append(
                f"Field 'version' must follow semver format (e.g., 1.0.0): got '{version}'"
            )

    # Validate license
    if 'license' in frontmatter:
        license_value = frontmatter['license']
        if not isinstance(license_value, str):
            errors.append("Field 'license' must be a string")
        elif license_value != 'Apache-2.0':
            errors.append(
                f"Field 'license' must be 'Apache-2.0' for community contributions: "
                f"got '{license_value}'"
            )

    # Validate tags
    if 'tags' in frontmatter:
        tags = frontmatter['tags']
        if not isinstance(tags, list):
            errors.append("Field 'tags' must be a list")
        elif len(tags) < 1:
            errors.append("Field 'tags' must contain at least 1 tag")
        elif len(tags) > 10:
            errors.append(f"Field 'tags' must contain at most 10 tags: got {len(tags)} tags")
        else:
            for i, tag in enumerate(tags):
                if not isinstance(tag, str):
                    errors.append(f"Tag at index {i} must be a string: got {type(tag).__name__}")
    else:
        errors.append("Missing required field: tags")

    # Validate token budget
    if 'token_budget' in frontmatter:
        token_budget = frontmatter['token_budget']
        if not isinstance(token_budget, int):
            errors.append("Field 'token_budget' must be an integer")
        elif token_budget < 800:
            errors.append(
                f"Field 'token_budget' must be at least 800: got {token_budget}"
            )
        elif token_budget > 5000:
            errors.append(
                f"Field 'token_budget' must be at most 5000: got {token_budget}"
            )
    else:
        errors.append("Missing required field: token_budget")

    # Extract content after frontmatter
    content_after_frontmatter = content[frontmatter_match.end():]

    # Validate required sections
    required_sections = ['## Purpose', '## Usage']
    for section in required_sections:
        if section not in content_after_frontmatter:
            errors.append(f"Missing required section: {section}")

    # Return validation result
    return len(errors) == 0, errors


def get_community_skills(claude_dir: Path) -> List[Dict]:
    """Get list of available community skills.

    Scans the community skills directory and returns metadata for all available
    community-contributed skills. Each skill entry includes name, version,
    author, description, tags, and installation status.

    Args:
        claude_dir: Path to the .claude directory

    Returns:
        List of dictionaries containing skill metadata. Each dictionary has:
        - name: Skill name
        - version: Skill version
        - author: Skill author
        - description: Skill description
        - tags: List of tags
        - license: License identifier
        - token_budget: Token budget
        - installed: Whether the skill is installed
        - rating: Average rating (if available)

    Example:
        >>> skills = get_community_skills(Path.home() / ".claude")
        >>> for skill in skills:
        ...     print(f"{skill['name']} v{skill['version']} by {skill['author']}")
    """
    if yaml is None:
        return []

    community_dir = claude_dir / "community" / "skills"
    if not community_dir.exists():
        return []

    skills: List[Dict] = []

    # Scan for skill files
    for skill_file in community_dir.glob("*.md"):
        try:
            content = skill_file.read_text(encoding="utf-8")

            # Extract frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
            if not frontmatter_match:
                continue

            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            if not isinstance(frontmatter, dict):
                continue

            # Check if skill is installed
            installed_path = claude_dir / "skills" / skill_file.name
            installed = installed_path.exists()

            # Load rating if available
            rating = None
            ratings_file = claude_dir / "community" / "ratings" / f"{skill_file.stem}.json"
            if ratings_file.exists():
                try:
                    ratings_data = json.loads(ratings_file.read_text(encoding="utf-8"))
                    if 'average' in ratings_data:
                        rating = ratings_data['average']
                except Exception:
                    pass

            # Build skill metadata
            skill_info = {
                'name': frontmatter.get('name', skill_file.stem),
                'version': frontmatter.get('version', 'unknown'),
                'author': frontmatter.get('author', 'unknown'),
                'description': frontmatter.get('description', ''),
                'tags': frontmatter.get('tags', []),
                'license': frontmatter.get('license', 'unknown'),
                'token_budget': frontmatter.get('token_budget', 0),
                'installed': installed,
                'rating': rating,
                'file': str(skill_file),
            }

            skills.append(skill_info)

        except Exception:
            # Skip invalid skill files
            continue

    # Sort by name
    skills.sort(key=lambda s: s['name'])

    return skills


def install_community_skill(skill_name: str, claude_dir: Path) -> bool:
    """Install a community skill to the local skills directory.

    Copies a community skill from the community/skills directory to the
    local skills directory, making it available for use. Validates the
    skill before installation.

    Args:
        skill_name: Name of the skill to install (without .md extension)
        claude_dir: Path to the .claude directory

    Returns:
        True if installation was successful, False otherwise

    Example:
        >>> if install_community_skill("react-hooks", Path.home() / ".claude"):
        ...     print("Skill installed successfully")
    """
    community_dir = claude_dir / "community" / "skills"
    skills_dir = claude_dir / "skills"

    # Ensure directories exist
    if not community_dir.exists():
        return False

    skills_dir.mkdir(parents=True, exist_ok=True)

    # Find skill file
    skill_file = community_dir / f"{skill_name}.md"
    if not skill_file.exists():
        return False

    # Validate skill before installation
    is_valid, errors = validate_contribution(skill_file)
    if not is_valid:
        return False

    # Copy to skills directory
    try:
        dest_file = skills_dir / f"{skill_name}.md"
        dest_file.write_text(skill_file.read_text(encoding="utf-8"), encoding="utf-8")
        return True
    except Exception:
        return False


def rate_skill(skill_name: str, rating: int, claude_dir: Path) -> bool:
    """Rate a community skill.

    Records a user rating for a community skill. Ratings are stored in the
    community/ratings directory and used to calculate average ratings.

    Args:
        skill_name: Name of the skill to rate (without .md extension)
        rating: Rating value (1-5 stars)
        claude_dir: Path to the .claude directory

    Returns:
        True if rating was recorded successfully, False otherwise

    Example:
        >>> if rate_skill("react-hooks", 5, Path.home() / ".claude"):
        ...     print("Rating recorded")
    """
    # Validate rating value
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return False

    ratings_dir = claude_dir / "community" / "ratings"
    ratings_dir.mkdir(parents=True, exist_ok=True)

    ratings_file = ratings_dir / f"{skill_name}.json"

    # Load existing ratings
    ratings_data: Dict = {'ratings': [], 'average': 0.0}
    if ratings_file.exists():
        try:
            ratings_data = json.loads(ratings_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Add new rating
    if 'ratings' not in ratings_data:
        ratings_data['ratings'] = []

    ratings_data['ratings'].append(rating)

    # Calculate average
    if ratings_data['ratings']:
        ratings_data['average'] = sum(ratings_data['ratings']) / len(ratings_data['ratings'])

    # Save ratings
    try:
        ratings_file.write_text(
            json.dumps(ratings_data, indent=2),
            encoding="utf-8"
        )
        return True
    except Exception:
        return False


def search_skills(query: str, tags: List[str], claude_dir: Path) -> List[Dict]:
    """Search for community skills by query and tags.

    Searches available community skills using a text query and optional tag
    filters. Returns matching skills sorted by relevance.

    Args:
        query: Search query string (searches name and description)
        tags: List of tags to filter by (empty list for no tag filtering)
        claude_dir: Path to the .claude directory

    Returns:
        List of matching skill metadata dictionaries, sorted by relevance

    Example:
        >>> results = search_skills("react", ["frontend", "hooks"], Path.home() / ".claude")
        >>> for skill in results:
        ...     print(f"Found: {skill['name']}")
    """
    # Get all community skills
    all_skills = get_community_skills(claude_dir)

    if not all_skills:
        return []

    # Normalize query
    query_lower = query.lower() if query else ""
    tags_lower = [tag.lower() for tag in tags] if tags else []

    # Filter skills
    matching_skills: List[Tuple[Dict, int]] = []

    for skill in all_skills:
        relevance = 0

        # Check tag filter
        if tags_lower:
            skill_tags_lower = [tag.lower() for tag in skill.get('tags', [])]
            if not any(tag in skill_tags_lower for tag in tags_lower):
                continue  # Skip skills that don't match tag filter

        # Calculate relevance score
        if query_lower:
            name_lower = skill.get('name', '').lower()
            description_lower = skill.get('description', '').lower()

            # Exact name match: +100
            if name_lower == query_lower:
                relevance += 100
            # Name contains query: +50
            elif query_lower in name_lower:
                relevance += 50
            # Description contains query: +10
            elif query_lower in description_lower:
                relevance += 10
            else:
                continue  # Skip skills that don't match query

        # Add tag match bonus
        if tags_lower:
            skill_tags_lower = [tag.lower() for tag in skill.get('tags', [])]
            matching_tags = sum(1 for tag in tags_lower if tag in skill_tags_lower)
            relevance += matching_tags * 5

        matching_skills.append((skill, relevance))

    # Sort by relevance (highest first)
    matching_skills.sort(key=lambda x: x[1], reverse=True)

    # Return skills without relevance scores
    return [skill for skill, _ in matching_skills]
