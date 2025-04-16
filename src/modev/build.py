import sys
from pathlib import Path
from marimo._ast.app import InternalApp
from marimo import App
import importlib
import typer
import yaml # Add yaml import
import tomllib # To read project name for default export dir
import re # Add re import for directive parsing
import ast # Add ast import for import analysis
from typing import List, Dict, Set, Tuple, Optional

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

def transform_imports(code: str, notebook_relative_path: str, target_file: str, project_name: str) -> str:
    """
    Currently only warns about potentially problematic imports without transformations.
    
    TRANSFORMATION TEMPORARILY DISABLED:
    The import transformation logic has been commented out for now
    and will be revisited in a future update.
    
    Args:
        code: The code string to transform
        notebook_relative_path: Path of the notebook relative to project root (for diagnostics)
        target_file: Path of the target file relative to export_dir
        project_name: The project name for absolute imports
        
    Returns:
        Original code string (transformations disabled)
    """
    if not code.strip() or "import " not in code:
        return code
        
    try:
        # Parse the code to an AST
        tree = ast.parse(code)
        
        # Track imports for warnings only (transformations disabled)
        # imports_to_transform = []
        
        # Check for problematic imports
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module if node.module else ""
                
                # --- TRANSFORMATION DISABLED ---
                # Case 1: Transform project_name.X imports to relative imports
                if module.startswith(f"{project_name}."):
                    # Currently just warn without transformation
                    typer.echo(f"  Note: Found project import: from {module} import ... (transformations disabled)")
                    # imports_to_transform.append({
                    #     'type': 'from',
                    #     'original': f"from {module}",
                    #     'replacement': f"from .{module[len(project_name)+1:]}",
                    #     'line': node.lineno
                    # })
                    # typer.echo(f"  Transforming: from {module} import ... -> from .{module[len(project_name)+1:]} import ...")
                
                # Case 2: Detect relative imports from notebook
                elif module.startswith('.'):
                    typer.secho(f"  Note: Using relative import '{module}' in {notebook_relative_path}", 
                               fg=typer.colors.YELLOW)
                
                # Case 3: Check for imports from potentially problematic locations
                elif module.startswith('nbs.'):
                    typer.secho(f"  Warning: Import from 'nbs.' in {notebook_relative_path}. " 
                               f"This will likely fail in exported modules. Consider restructuring imports.", 
                               fg=typer.colors.RED)
                
            elif isinstance(node, ast.Import):
                for name in node.names:
                    # --- TRANSFORMATION DISABLED ---
                    # Handle direct imports of project modules: import project_name.module
                    if name.name.startswith(f"{project_name}."):
                        # Currently just warn without transformation
                        typer.echo(f"  Note: Found project import: import {name.name} (transformations disabled)")
                        # Special handling for imports with aliases was here
                    
                    elif name.name.startswith('nbs.'):
                        typer.secho(f"  Warning: Import of 'nbs.' module in {notebook_relative_path}. "
                                   f"This will likely fail in exported modules.", 
                                   fg=typer.colors.RED)
        
        # --- TRANSFORMATION DISABLED ---
        # Transformation code was here
        # Currently just return the original code
        return code
            
    except SyntaxError:
        typer.secho(f"  Warning: Syntax error when analyzing imports in {notebook_relative_path}. "
                   f"Imports may need manual adjustment.", fg=typer.colors.RED)
        return code
    except Exception as e:
        typer.secho(f"  Warning: Error analyzing imports in {notebook_relative_path}: {e}. "
                   f"Using original imports.", fg=typer.colors.RED)
        return code

def extract_export_details(app: App, project_root: Path, project_name: str, notebook_relative_path: str) -> tuple[str | None, str, set[str]]:
    """
    Extracts target filename from the first #| default_exp directive encountered,
    and Python code marked with '#| export' from a marimo App.

    Args:
        app: The marimo App object
        project_root: Path to the project root
        project_name: Project name for import processing
        notebook_relative_path: Path of notebook relative to project root

    Returns: (target_filename | None, code_export, all_defs)
    """
    target_filename: str | None = None
    code_export: str = ""
    all_defs: set[str] = set()
    relative_notebook_path_str = notebook_relative_path # Using the passed relative path

    try:
        internal_app = InternalApp(app)
        
        # --- 1. Find the first #| default_exp directive --- 
        # Iterate through cells (order might approximate definition, but we stop on first find)
        for cell in internal_app.graph.cells.values():
            if cell.language == "python":
                # Regex to find #| default_exp name or #| default_exp name.py
                match = re.search(r"^#\|\s*default_exp\s+(\S+)", cell.code, re.MULTILINE)
                if match:
                    target_name = match.group(1).strip()
                    if not target_name:
                        typer.secho(f"  Warning: Found '#| default_exp' directive but no filename specified in cell {cell.cell_id} of {getattr(app, '_filename', '?')}", fg=typer.colors.YELLOW)
                    else:
                        # Ensure it ends with .py
                        if not target_name.endswith('.py'):
                            target_name += '.py'
                        target_filename = target_name
                        typer.echo(f"  Found export directive in cell {cell.cell_id}: target filename set to '{target_filename}'")
                    break # Stop searching once the first directive is found and processed

        # --- 2. Extract #| export code from all cells (in execution order) --- 
        # Determine the relative path of the notebook file once (for origin comments)
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

        order = internal_app.execution_order # Use execution order for export extraction
        export_cells = {
            k: v for k, v in internal_app.graph.cells.items()
            if v.language == "python" and "#| export" in v.code # Filter for export tag
        }

        for cell_id in order:
            if cell_id in export_cells:
                cell = export_cells[cell_id]
                origin_comment = f"# Exported from {relative_notebook_path_str} (cell ID: {cell.cell_id})"
                cleaned_code = cell.code.replace("#| export", origin_comment, 1).strip()

                if cleaned_code:
                    # Apply import transformations
                    if target_filename:
                        target_path = target_filename
                    else:
                        # Default to using notebook name if no target specified
                        target_path = str(Path(notebook_relative_path).with_suffix('.py').name)
                        
                    transformed_code = transform_imports(
                        cleaned_code, 
                        notebook_relative_path, 
                        target_path, 
                        project_name
                    )
                    
                    if not transformed_code.startswith(origin_comment):
                         code_export += origin_comment + "\n" + transformed_code + "\n\n"
                    else:
                         code_export += transformed_code + "\n\n"

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
    written_files = set()

    try:
        project_root = find_project_root()
        
        # Load configuration
        nbs_dir, output_base_dir = load_config(project_root)
        
        # Determine project name for import handling
        project_name = project_root.name # Default to directory name
        pyproject_path = project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    project_name = data.get("project", {}).get("name", project_name)
            except Exception:
                pass # Ignore errors, just use the default

        # Ensure export directory exists
        output_base_dir.mkdir(parents=True, exist_ok=True)

        # Add project root and source dir to Python path
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
                try:
                    relative_notebook_path = py_file.relative_to(nbs_dir)
                    relative_path_for_import = py_file.relative_to(project_root)
                    notebook_rel_str = str(relative_path_for_import).replace('\\', '/')

                    if py_file.name == '__init__.py':
                        continue

                    module_name = '.'.join(relative_path_for_import.with_suffix('').parts)
                    default_output_path = output_base_dir / relative_notebook_path

                    try:
                        module = importlib.import_module(module_name)

                        if hasattr(module, 'app') and isinstance(getattr(module, 'app'), App):
                            app_object = getattr(module, 'app')
                            
                            # Pass project name and notebook_rel_str to extract_export_details
                            target_filename, file_code, defined_names = extract_export_details(
                                app_object, 
                                project_root, 
                                project_name,  # Using the project_name from above
                                notebook_rel_str
                            )

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

                except ValueError as e:
                    typer.secho(f"Warning: Could not determine relative path for {py_file} within {nbs_dir} or {project_root}. Skipping. Error: {e}", fg=typer.colors.YELLOW)
                    continue
                except Exception as e:
                    typer.secho(f"Warning: Error calculating paths for {py_file}. Skipping. Error: {e}", fg=typer.colors.YELLOW)
                    continue

        typer.echo(f"\n--- Summary ---")
        typer.echo(f"Processed {processed_files_count}/{len(python_files)} Python files from {nbs_dir}.")
        typer.echo(f"Successfully exported code to {exported_files_count} files in {output_base_dir}.")

    except FileNotFoundError as e:
        typer.secho(f"Error: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
    except Exception as e:
        typer.secho(f"An unexpected error occurred during the build process: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    typer.echo("Build process finished.")

