# 🚀 python-modev

A development environment that uses Marimo notebooks as your primary development interface, inspired by nbdev. This tool allows you to write and organize your code in Marimo notebooks while maintaining a clean, exportable Python package structure.

## 📦 Installation

We recommend using [UV](https://github.com/astral-sh/uv) for installation and package management as it provides better performance and reliability:

```bash
# Install UV if you haven't already
pip install uv

# Install python-modev
uv pip install python-modev
```

For library development, you can initialize a new project with UV:

```bash
uv init --lib
```

## 🚀 Quick Start

1. Initialize a new project:
```bash
modev init
```

2. Start your Marimo notebook:
```bash
marimo edit
```

3. Export your code to Python files:
```bash
modev export
```

## 📁 Project Structure

After initialization, your project will have the following structure:
```
your-project/
├── modev.yaml        # Configuration file
├── nbs/              # Your Marimo notebooks
└── src/your-project  # Exported Python files
```

## ⚙️ Configuration

The `modev.yaml` file controls how your code is exported from notebooks to Python files. Here's an example configuration:

```yaml
paths:
  - source: notebooks/your_notebook.py
    destination: src/your_module/
```

### Configuration Options

- `source`: Path to your Marimo notebook
- `destination`: Where to export the Python files
- `export_type`: 
  - `module`: Export as a Python module (creates `__init__.py`)
  - `script`: Export as a standalone script

## 📝 Export Directives

python-modev uses special directives in your Marimo notebooks to control code export:

### `#| export` Directive

Use this directive to mark cells that should be exported to Python files:

```python
#| export
def my_function():
    """This function will be exported"""
    return "Hello, world!"
```

- Place `#| export` at the beginning of any cell you want to export
- The exported code will include an origin comment showing which notebook and cell it came from
- All exported code from a notebook will be combined into a single Python file

### `#| default_exp` Directive

Use this directive to specify the target filename for exported code:

```python
#| default_exp my_module
```

- Place this directive in any cell (usually at the top of your notebook)
- The first `#| default_exp` directive found will determine the output filename
- If no `#| default_exp` is found, the notebook's name will be used
- The `.py` extension is optional (will be added automatically if missing)

### Example Notebook Structure

Initial cell
```python
#| default_exp my_module.py
```

Following cells
```python
#| export
def public_function():
    """This will be included in __all__"""
    return "Public API"
```
```python
#| export
def _private_function():
    """This won't be included in __all__"""
    return "Internal use only"
```

## 🛠️ Usage

### Initializing a Project

```bash
modev init
```

This command:
- Creates a basic project structure
- Sets up a default `modev.yaml`
- Initializes necessary directories

### Exporting Code

```bash
modev export
```

This command:
- Reads your Marimo notebooks
- Extracts Python code marked with `#| export`
- Exports to the specified destinations in `modev.yaml`
- Automatically generates `__all__` based on exported names (excluding those starting with `_`)

## 💡 Best Practices

1. **Notebook Organization**:
   - Keep related code in the same notebook
   - Use clear cell markers to separate different components
   - Document your code using Marimo's markdown cells

2. **Export Configuration**:
   - Group related functionality in the same destination
   - Use module exports for packages
   - Use script exports for standalone utilities

3. **Development Workflow**:
   - Write and test code in Marimo notebooks
   - Export frequently to ensure your Python files stay in sync
   - Use version control to track changes in both notebooks and exported files

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
