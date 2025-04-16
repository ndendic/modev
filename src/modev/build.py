import sys
from pathlib import Path
from marimo._ast.app import InternalApp
from marimo import App
import importlib
import typer
import yaml # Add yaml import
import tomllib # To read project name for default export dir
import re # Add re import for directive parsing

# --- Helper Functions ---
def find_project_root() -> Path:
    """Searches upwards from the current file to find the project root directory.
       Looks for modev.yaml or pyproject.toml as markers.
    """
    current_path = Path(__file__).resolve()
    check_path = current_path
    # Handle running from cwd if installed (simple heuristic)
    if 'site-packages' in str(current_path) or '.venv' in str(current_path):
        check_path = Path.cwd()

    while True:
        # Look for configuration or project file
        if (check_path / 'modev.yaml').exists() or (check_path / 'pyproject.toml').exists():
            # typer.echo(f"Project root identified: {check_path} (found modev.yaml or pyproject.toml)")
            return check_path

        parent_path = check_path.parent
        if parent_path == check_path:
            # If we reach the root without finding markers, use CWD as fallback
            cwd = Path.cwd()
            typer.secho(f"Could not find modev.yaml or pyproject.toml in ancestors. Using current working directory as project root: {cwd}", fg=typer.colors.YELLOW)
            return cwd
        check_path = parent_path

def load_config(project_root: Path) -> tuple[Path, Path]:
    """Loads configuration from modev.yaml, falling back to defaults.
       Returns (notebooks_dir_path, export_dir_path).
    """
    config_path = project_root / "modev.yaml"
    
    # Determine default project name for export dir fallback
    project_name = project_root.name # Default to root folder name
    pyproject_path = project_root / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                project_name = data.get("project", {}).get("name", project_name)
        except Exception:
            pass # Ignore errors reading pyproject, just use folder name

    default_nbs_dir = "nbs"
    default_export_dir = f"src/{project_name}" # Default export dir

    config = {}
    if config_path.exists():
        typer.echo(f"Loading configuration from: {config_path}")
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            typer.secho(f"Warning: Error parsing {config_path}: {e}. Using default paths.", fg=typer.colors.YELLOW)
        except IOError as e:
            typer.secho(f"Warning: Could not read {config_path}: {e}. Using default paths.", fg=typer.colors.YELLOW)
        except Exception as e:
             typer.secho(f"Warning: Unexpected error reading {config_path}: {e}. Using default paths.", fg=typer.colors.YELLOW)
    else:
        typer.echo(f"Configuration file {config_path} not found. Using default paths.")

    nbs_dir_rel = config.get('notebooks_dir', default_nbs_dir)
    export_dir_rel = config.get('export_dir', default_export_dir)

    # Resolve to absolute paths relative to project root
    nbs_dir_path = (project_root / nbs_dir_rel).resolve()
    export_dir_path = (project_root / export_dir_rel).resolve()

    typer.echo(f"  Using Notebooks directory: {nbs_dir_path}")
    typer.echo(f"  Using Export directory:    {export_dir_path}")

    return nbs_dir_path, export_dir_path

def extract_export_details(app: App, project_root: Path) -> tuple[str | None, str, set[str]]:
    """
    Extracts target filename from the first cell's #| default_exp directive (if present),
    and Python code marked with '#| export' from a marimo App.

    Returns: (target_filename | None, code_export, all_defs)
    """
    target_filename: str | None = None
    code_export: str = ""
    all_defs: set[str] = set()
    relative_notebook_path_str = "unknown_notebook" # Default path string

    try:
        internal_app = InternalApp(app)
        order = internal_app.execution_order
        export_cells = {
            k: v for k, v in internal_app.graph.cells.items()
            if v.language == "python" and "#| export" in v.code
        }

        cell_ids_definition_order = list(export_cells.keys())

        # --- 1. Check first cell for #| default_exp directive --- 
        if cell_ids_definition_order:
            first_cell_id = cell_ids_definition_order[0]
            if first_cell_id in internal_app.graph.cells:
                first_cell = internal_app.graph.cells[first_cell_id]
                if first_cell.language == "python":
                    # Regex to find #| default_exp name or #| default_exp name.py
                    match = re.search(r"^#\|\s*default_exp\s+(\S+)", first_cell.code, re.MULTILINE)
                    if match:
                        target_name = match.group(1).strip()
                        if not target_name:
                            typer.secho(f"  Warning: Found '#| default_exp' directive but no filename specified in first cell of {getattr(app, '_filename', '?')}", fg=typer.colors.YELLOW)
                        else:
                            # Ensure it ends with .py
                            if not target_name.endswith('.py'):
                                target_name += '.py'
                            target_filename = target_name
                            typer.echo(f"  Found export directive: target filename set to '{target_filename}'")

        # --- 2. Extract ## Export code from all cells (in execution order) --- 
        # Determine the relative path of the notebook file once
        if hasattr(app, '_filename') and app._filename:
            try:
                abs_notebook_path = Path(app._filename).resolve()
                relative_notebook_path = abs_notebook_path.relative_to(project_root)
                relative_notebook_path_str = str(relative_notebook_path).replace('\\', '/') # Normalize slashes
            except ValueError:
                 typer.secho(f"  Warning: Notebook path {app._filename} is not relative to project root {project_root}. Using absolute path for origin comment.", fg=typer.colors.YELLOW)
                 relative_notebook_path_str = str(abs_notebook_path)
            except Exception as path_e:
                 typer.secho(f"  Warning: Could not determine relative path for {app._filename}: {path_e}. Using absolute path for origin comment.", fg=typer.colors.YELLOW)
                 relative_notebook_path_str = str(app._filename) # Fallback
        else:
             typer.secho("  Warning: Cannot determine notebook filename from app object. Origin comment will be incomplete.", fg=typer.colors.YELLOW)

        order = internal_app.execution_order
        export_cells = {
            k: v for k, v in internal_app.graph.cells.items()
            if v.language == "python" and "#| export" in v.code
        }

        for cell_id in order:
            if cell_id in export_cells:
                cell = export_cells[cell_id]
                origin_comment = f"# Exported from {relative_notebook_path_str} (cell ID: {cell.cell_id})"
                cleaned_code = cell.code.replace("#| export", origin_comment, 1).strip()

                if cleaned_code:
                     if not cleaned_code.startswith(origin_comment):
                          code_export += origin_comment + "\n" + cleaned_code + "\n\n"
                     else:
                          code_export += cleaned_code + "\n\n"

                if hasattr(cell, 'defs'):
                     all_defs.update(cell.defs)
                else:
                     typer.secho(f"  Warning: Cell {cell_id} lacks 'defs' attribute. Cannot extract names for __all__ from this cell.", fg=typer.colors.YELLOW)

        return target_filename, code_export.strip(), all_defs

    except Exception as e:
        notebook_name = getattr(app, '_filename', 'unknown notebook')
        typer.secho(f"  Error processing app from {notebook_name} with marimo: {e}", fg=typer.colors.YELLOW)
        return None, "", set() # Return defaults on error

def run_export():
    """
    Finds marimo apps based on modev.yaml config, extracts tagged code using #| default_exp
    or notebook filename, generates __all__, adds origin comments, and writes to the export directory.
    """
    processed_files_count = 0
    exported_files_count = 0
    written_files = set() # Keep track of files written via default_exp to warn on overwrite

    try:
        project_root = find_project_root()
        # typer.echo(f"Project root found: {project_root}") # Less verbose now

        # Load configuration
        nbs_dir, output_base_dir = load_config(project_root)

        # Ensure export directory exists
        output_base_dir.mkdir(parents=True, exist_ok=True)

        # Add project root and source dir to Python path
        # ... (sys.path modification remains the same)
        project_root_str = str(project_root)
        src_dir_str = str(project_root / 'src') # Standard src dir

        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        if (project_root / 'src').exists() and src_dir_str not in sys.path:
             sys.path.insert(0, src_dir_str)

        if not nbs_dir.is_dir():
            typer.secho(f"Error: Configured notebooks directory does not exist or is not a directory: {nbs_dir}", fg=typer.colors.RED)
            raise typer.Exit(code=1)

        python_files = list(nbs_dir.rglob('*.py'))
        typer.echo(f"Found {len(python_files)} Python files in {nbs_dir}")

        with typer.progressbar(python_files, label="Processing notebooks") as progress:
            for py_file in progress:
                processed_files_count += 1
                target_filename: str | None = None
                output_file_path: Path | None = None

                try:
                    relative_notebook_path = py_file.relative_to(nbs_dir)
                    relative_path_for_import = py_file.relative_to(project_root)

                    if py_file.name == '__init__.py':
                        continue

                    module_name = '.'.join(relative_path_for_import.with_suffix('').parts)
                    # Default output path (used if no directive)
                    default_output_path = output_base_dir / relative_notebook_path

                except ValueError as e:
                    typer.secho(f"Warning: Could not determine relative path for {py_file} within {nbs_dir} or {project_root}. Skipping. Error: {e}", fg=typer.colors.YELLOW)
                    continue
                except Exception as e:
                    typer.secho(f"Warning: Error calculating paths for {py_file}. Skipping. Error: {e}", fg=typer.colors.YELLOW)
                    continue

                try:
                    module = importlib.import_module(module_name)

                    if hasattr(module, 'app') and isinstance(getattr(module, 'app'), App):
                        app_object = getattr(module, 'app')
                        # Call the new function to get details
                        target_filename, file_code, defined_names = extract_export_details(app_object, project_root)

                        if file_code: # Only proceed if there is code tagged with #| export
                            # Determine final output path
                            if target_filename:
                                output_file_path = output_base_dir / target_filename
                                # Warn if this specific filename was already written by another notebook via default_exp
                                if output_file_path in written_files:
                                     typer.secho(f"  Warning: Overwriting {output_file_path} which was already generated by another notebook's '#| default_exp {target_filename}' directive.", fg=typer.colors.YELLOW)
                                elif output_file_path.exists():
                                    # Warn if the file exists but wasn't from *this run* (less severe warning)
                                     typer.secho(f"  Warning: Overwriting existing file {output_file_path} specified by '#| default_exp {target_filename}' in {py_file.name}", fg=typer.colors.YELLOW)
                                written_files.add(output_file_path) # Track files written via directive
                            else:
                                output_file_path = default_output_path
                                # Optional: Warn if default path overwrites existing file?
                                # if output_file_path.exists():
                                #     typer.secho(f"  Warning: Overwriting existing file {output_file_path} (using default name from {py_file.name})", fg=typer.colors.YELLOW)

                            # Prepare code with __all__
                            public_names = {name for name in defined_names if not name.startswith('_')}
                            dunder_all_list = sorted(list(public_names))
                            dunder_all_string = f"__all__ = {repr(dunder_all_list)}\n\n"
                            final_code_to_write = dunder_all_string + file_code

                            # Write the file
                            try:
                                output_file_path.parent.mkdir(parents=True, exist_ok=True)
                                output_file_path.write_text(final_code_to_write)
                                exported_files_count += 1
                            except IOError as e:
                                typer.secho(f"  Error writing to output file {output_file_path}: {e}", fg=typer.colors.RED)
                            except Exception as e:
                                typer.secho(f"  Unexpected error writing file {output_file_path}: {e}", fg=typer.colors.RED)

                except ImportError as e:
                    typer.secho(f"  Error importing module {module_name} from {py_file}: {e}", fg=typer.colors.RED)
                except Exception as e:
                    typer.secho(f"  Unexpected error processing file {py_file}: {e}", fg=typer.colors.RED)

        # ... (Summary remains the same)
        typer.echo(f"\n--- Summary ---")
        typer.echo(f"Processed {processed_files_count}/{len(python_files)} Python files from {nbs_dir}.")
        typer.echo(f"Successfully exported code to {exported_files_count} files in {output_base_dir}.")

    # ... (Error handling remains the same)
    except FileNotFoundError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during the build process: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("Build process finished.")

