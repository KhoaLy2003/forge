from core.progress import step


def test_step_prints_numbered_message(capsys):
    step("Writing project files...", 1, 3)
    assert capsys.readouterr().out == "[1/3] Writing project files...\n"
