from pathlib import Path

from forge_web.core.tree_preview import confirm, format_tree


def test_format_tree_renders_box_drawing_tree_sorted_alphabetically():
    paths = [Path("b/file.txt"), Path("a.txt")]
    assert format_tree(paths) == "a.txt\nb\n└── file.txt"


def test_format_tree_nests_multiple_levels_with_correct_connectors():
    paths = [
        Path("package.json"),
        Path("src/components/ui/button.tsx"),
        Path("src/styles/theme.css"),
    ]
    assert format_tree(paths) == (
        "package.json\n"
        "src\n"
        "├── components\n"
        "│   └── ui\n"
        "│       └── button.tsx\n"
        "└── styles\n"
        "    └── theme.css"
    )


def test_confirm_returns_true_on_yes(capsys):
    result = confirm("tree here", prompt_fn=lambda _: "y")
    assert result is True
    assert "tree here" in capsys.readouterr().out


def test_confirm_returns_true_on_full_word_yes():
    assert confirm("tree", prompt_fn=lambda _: "YES") is True


def test_confirm_returns_false_on_no():
    assert confirm("tree", prompt_fn=lambda _: "n") is False


def test_confirm_returns_false_on_empty_input():
    assert confirm("tree", prompt_fn=lambda _: "") is False
