import sys
from pathlib import Path
from marimo._ast.app import InternalApp
from marimo import App
import importlib
import typer # Import typer for potential feedback/coloring later

# --- Helper Functions ---

def find_project_root() -> Path:
    """Searches upwards from the current file to find the project root directory."""
    current_path = Path(__file__).resolve()
    # Adjust search start point if running as part of an installed package
    # This might need refinement depending on packaging structure
    if 'site-packages' in str(current_path):
         # A simple heuristic: assume CWD is the project if installed
         # A better approach might involve config files or env vars
        check_path = Path.cwd()
    else:
        check_path = current_path

    while True:
        # Look for a common marker, like pyproject.toml or .git, along with nbs/src
        is_root = (check_path / 'pyproject.toml').exists() or (check_path / '.git').is_dir()
        has_dirs = (check_path / 'src').is_dir() and (check_path / 'nbs').is_dir()

        if is_root and has_dirs:
             typer.echo(f"Project root heuristic found: {check_path}")
             return check_path
        # Fallback to original logic if marker not found but dirs exist
        if has_dirs and not is_root and check_path == current_path.parent: # Only original logic for first parent check
             typer.echo(f"Project root fallback found: {check_path}")
             return check_path

        parent_path = check_path.parent
        if parent_path == check_path:
            raise FileNotFoundError("Could not reliably determine project root. Looked for src/, nbs/, and pyproject.toml or .git.")
        check_path = parent_path


def export_code_and_defs(app: App, project_root: Path) -> tuple[str, set[str]]:
    """
    Extracts Python code marked with '## Export' from a marimo App, adding origin comments,
    and returns the code string and a set of defined names in those cells.
    """
    code_export = ""
    all_defs: set[str] = set()
    relative_notebook_path_str = "unknown_notebook" # Default path string

    try:
        # Determine the relative path of the notebook file once
        if hasattr(app, '_filename') and app._filename:
            try:
                abs_notebook_path = Path(app._filename).resolve()
                relative_notebook_path = abs_notebook_path.relative_to(project_root)
                relative_notebook_path_str = str(relative_notebook_path).replace('\\', '/') # Normalize slashes
            except ValueError:
                 typer.secho(f"  Warning: Notebook path {app._filename} is not relative to project root {project_root}. Using absolute path.", fg=typer.colors.YELLOW)
                 relative_notebook_path_str = str(abs_notebook_path)
            except Exception as path_e:
                 typer.secho(f"  Warning: Could not determine relative path for {app._filename}: {path_e}. Using absolute path.", fg=typer.colors.YELLOW)
                 relative_notebook_path_str = str(app._filename) # Fallback to original if Path fails
        else:
             typer.secho("  Warning: Cannot determine notebook filename from app object. Origin comment will be incomplete.", fg=typer.colors.YELLOW)


        internal_app = InternalApp(app)
        order = internal_app.execution_order
        export_cells = {
            k: v for k, v in internal_app.graph.cells.items()
            if v.language == "python" and "## Export" in v.code
        }

        for cell_id in order:
            if cell_id in export_cells:
                cell = export_cells[cell_id]
                # Construct the replacement comment string
                origin_comment = f"# Exported from {relative_notebook_path_str} (cell ID: {cell.cell_id})"
                # Replace '## Export' with the origin comment
                # Ensure only the first occurrence is replaced if '## Export' appears multiple times
                cleaned_code = cell.code.replace("## Export", origin_comment, 1).strip()

                if cleaned_code:
                    # Add a newline before the code block if it doesn't start with the comment
                    if not cleaned_code.startswith(origin_comment):
                         code_export += origin_comment + "\n" + cleaned_code + "\n\n"
                    else: # Append only if the code wasn't just the comment itself
                         code_export += cleaned_code + "\n\n"


                if hasattr(cell, 'defs'):
                     all_defs.update(cell.defs)
                else:
                     typer.secho(f"  Warning: Cell {cell_id} lacks 'defs' attribute. Cannot extract names for __all__ from this cell.", fg=typer.colors.YELLOW)


        return code_export.strip(), all_defs
    except Exception as e:
        typer.secho(f"  Error processing app with marimo: {e}", fg=typer.colors.YELLOW)
        return "", set()


def run_export():
    """
    Finds marimo apps in nbs/*.py, extracts tagged code with origin comments,
    generates __all__ from cell definitions, and writes to corresponding src/modev/*.py files.
    """
    processed_files_count = 0
    exported_files_count = 0

    try:
        project_root = find_project_root()
        typer.echo(f"Project root found: {project_root}")

        nbs_dir = project_root / 'nbs'
        output_base_dir = project_root / 'src' / 'modev'
        src_dir_str = str(project_root / 'src')

        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        if src_dir_str not in sys.path:
            sys.path.insert(0, src_dir_str)

        python_files = list(nbs_dir.rglob('*.py'))
        typer.echo(f"Found {len(python_files)} Python files in {nbs_dir}")

        with typer.progressbar(python_files, label="Processing files") as progress:
            for py_file in progress:
                processed_files_count += 1
                try:
                    relative_notebook_path = py_file.relative_to(nbs_dir)
                    relative_path_for_import = py_file.relative_to(project_root)

                    if py_file.name == '__init__.py':
                        continue

                    module_name = '.'.join(relative_path_for_import.with_suffix('').parts)
                    output_file_path = output_base_dir / relative_notebook_path

                except ValueError:
                    typer.secho(f"Warning: Could not determine relative path for {py_file}. Skipping.", fg=typer.colors.YELLOW)
                    continue

                try:
                    module = importlib.import_module(module_name)

                    if hasattr(module, 'app'):
                        app_object = getattr(module, 'app')
                        if isinstance(app_object, App):
                            # Pass project_root to the export function
                            file_code, defined_names = export_code_and_defs(app_object, project_root)

                            if file_code:
                                public_names = {name for name in defined_names if not name.startswith('_')}
                                dunder_all_list = sorted(list(public_names))
                                dunder_all_string = f"__all__ = {repr(dunder_all_list)}\n\n"
                                final_code_to_write = dunder_all_string + file_code

                                try:
                                    output_file_path.parent.mkdir(parents=True, exist_ok=True)
                                    output_file_path.write_text(final_code_to_write)
                                    exported_files_count += 1
                                except IOError as e:
                                    typer.secho(f"  Error writing to output file {output_file_path}: {e}", fg=typer.colors.RED)
                                except Exception as e:
                                     typer.secho(f"  Unexpected error writing file {output_file_path}: {e}", fg=typer.colors.RED)

                except ImportError as e:
                    typer.secho(f"  Error importing module {module_name}: {e}", fg=typer.colors.RED)
                except Exception as e:
                    typer.secho(f"  Unexpected error processing file {py_file}: {e}", fg=typer.colors.RED)

        typer.echo(f"\n--- Summary ---")
        typer.echo(f"Processed {processed_files_count}/{len(python_files)} Python files.")
        typer.echo(f"Successfully exported code (with __all__ and origin comments) to {exported_files_count} files in {output_base_dir}.")

    except FileNotFoundError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during the build process: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("Build process finished.")


# Remove the old __main__ block if it exists
# if __name__ == "__main__":
#    run_export() # No longer run directly

