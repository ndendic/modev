import typer
from .build import run_export # Use relative import
import tomllib # Use tomllib for Python >= 3.11
from pathlib import Path
import sys
import yaml # Add yaml import

# Template content for the initial notebook
NOTEBOOK_TEMPLATE = '''import marimo

# __generated_with = "0.1.0" # Adjust version as needed
app = marimo.App(width="medium")

@app.cell
def _():
    #| default_exp core
    return

@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    # Customize this title for your project!
    mo.md(r"""# Your Project Title Here""")
    return


@app.cell
def example_export():
    ## Export
    # Define functions or variables here that you want to export
    def hello() -> str:
        return "Hello from your new modev project!"
    return (hello,)


if __name__ == "__main__":
    app.run()
'''

app = typer.Typer(
    help="Modev CLI: Tools for managing marimo notebooks and code export."
)
@app.command()
def init():
    """
    Initialize modev: Creates nbs/core.py and modev.yaml if they don't exist.
    """
    project_root = Path.cwd()
    pyproject_path = project_root / "pyproject.toml"
    config_path = project_root / "modev.yaml"
    nbs_dir = project_root / "nbs"
    core_notebook_path = nbs_dir / "core.py"

    # --- Determine Project Name (for default export path) --- 
    project_name = project_root.name # Default to directory name
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project_name = data.get("project", {}).get("name", project_name)
        except Exception as e:
            typer.secho(f"Warning: Could not read project name from {pyproject_path}: {e}. Using directory name '{project_name}'.", fg=typer.colors.YELLOW)

    default_export_dir = Path("src") / project_name

    # --- Create nbs directory and core.py --- 
    try:
        if not nbs_dir.exists():
            typer.echo(f"Creating notebooks directory: {nbs_dir}")
            nbs_dir.mkdir(parents=True)
        else:
            typer.echo(f"Notebooks directory already exists: {nbs_dir}")

        if not core_notebook_path.exists():
            typer.echo(f"Creating initial notebook: {core_notebook_path}")
            core_notebook_path.write_text(NOTEBOOK_TEMPLATE)
        else:
            typer.echo(f"Initial notebook already exists: {core_notebook_path}")

    except OSError as e:
        typer.secho(f"Error creating notebooks directory or file: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    # --- Create modev.yaml configuration file --- 
    if not config_path.exists():
        typer.echo(f"Creating configuration file: {config_path}")
        config_data = {
            'notebooks_dir': 'nbs',
            'export_dir': str(default_export_dir).replace('\\', '/') # Use posix-style path
        }
        try:
            with open(config_path, 'w') as f:
                yaml.dump(config_data, f, default_flow_style=False)
        except IOError as e:
            typer.secho(f"Error writing configuration file {config_path}: {e}", fg=typer.colors.RED)
            # Continue even if config writing fails, nbs might be useful
        except Exception as e:
             typer.secho(f"An unexpected error occurred writing {config_path}: {e}", fg=typer.colors.RED)
    else:
        typer.echo(f"Configuration file already exists: {config_path}")

    typer.echo("\nModev initialization complete.")
    typer.echo(f"- Notebooks directory: {nbs_dir}")
    typer.echo(f"- Config file: {config_path}")

@app.command()
def export():
    """
    Finds marimo apps in nbs/*.py, extracts tagged code, and writes to src/modev/core.py.
    """
    try:
        run_export() # This will need to be updated to use modev.yaml
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