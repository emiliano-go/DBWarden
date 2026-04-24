from rich.console import Console


console = Console(force_terminal=True, no_color=False)


def info(message: str) -> None:
    console.print(message, style="cyan")


def success(message: str) -> None:
    console.print(message, style="green")


def warning(message: str) -> None:
    console.print(message, style="yellow")


def error(message: str) -> None:
    console.print(message, style="bold red")
