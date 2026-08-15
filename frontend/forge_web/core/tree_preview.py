"""Render a resolved file tree as a preview and confirm with the user before writing it to disk."""

from pathlib import Path


def _build_tree(paths: list[Path]) -> dict:
    """Build a nested dict from a flat list of file paths (dirs are implied by their children)."""
    root: dict = {}
    for path in paths:
        node = root
        for part in path.parts:
            node = node.setdefault(part, {})
    return root


def _render_node(node: dict, prefix: str = "") -> list[str]:
    """Recursively render one level of the tree with box-drawing connectors."""
    lines = []
    names = sorted(node)
    for i, name in enumerate(names):
        is_last = i == len(names) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{name}")
        child_prefix = prefix + ("    " if is_last else "│   ")
        lines.extend(_render_node(node[name], child_prefix))
    return lines


def format_tree(paths: list[Path]) -> str:
    """Render a flat list of file paths as a box-drawing tree, like the `tree` command."""
    tree = _build_tree(paths)
    lines = []
    for name in sorted(tree):
        lines.append(name)
        lines.extend(_render_node(tree[name], ""))
    return "\n".join(lines)


def confirm(tree_text: str, prompt_fn=input) -> bool:
    """Print the tree text and ask the user to confirm generation; return True only on y/yes."""
    print(tree_text)
    answer = prompt_fn("Generate this project? [y/N]: ")
    return answer.strip().lower() in ("y", "yes")
