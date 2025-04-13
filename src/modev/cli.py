import typer
from .build import run_export # Use relative import

app = typer.Typer(
    help="Modev CLI: Tools for managing marimo notebooks and code export."
)
@app.command()
def init():
    """
    Initialize a new modev environment.
    """
    print("This should initialize a new modev environment.")

@app.command()
def export():
    """
    Finds marimo apps in nbs/*.py, extracts tagged code, and writes to src/modev/core.py.
    """
    try:
        run_export()
    except typer.Exit:
        # Catch exits from run_export to prevent further processing if needed
        raise # Re-raise the Exit exception
    except Exception as e:
        # Catch any unexpected errors not handled in run_export
        typer.secho(f"CLI Error: An unexpected error occurred: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

# Add other commands here later if needed
# @app.command("another_command")
# def ...

if __name__ == "__main__":
    app() 