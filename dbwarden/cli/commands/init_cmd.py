import typer

from dbwarden.cli.app import app
from dbwarden.commands import handle_init


@app.command()
def init(
    database: str | None = typer.Option(
        None, "--database", "-d", help="Database name to create migration directory for"
    ),
):
    """Initialize the migrations directory."""
    handle_init(database=database)
