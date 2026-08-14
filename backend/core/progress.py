"""Print numbered progress messages for the steps of a generation run."""


def step(message: str, index: int, total: int) -> None:
    """Print a message prefixed with its position among the total number of steps."""
    print(f"[{index}/{total}] {message}")
