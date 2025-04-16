# from marimo._ast.app import InternalApp
# from core import app
# from pathlib import Path

# # Lets move out the code first

# order = InternalApp(app).execution_order

# for k, v in InternalApp(app).graph.cells.items():
#     print(f"{app._filename}")
#     print(f"\nCELL ID: {k} - {v.cell_id}")
#     print(f"Language: {v.language}")
#     print(f"Code: {v.code}")
#     print(f"Defs: {v.defs}")
#     print(f"Refs: {v.refs}")
#     print(f"Variable data: {v.variable_data}")
#     print(f"Deleted refs: {v.deleted_refs}")
#     print(f"Body: {v.body}")
#     print(f"Last expr: {v.last_expr}")
#     print(f"Imports: {v.imports}")
#     print(f"Output: {v.output}")

#     print("--------------------------------")

# # codes = {k: v.code for k, v in InternalApp(app).graph.cells.items() if v.language=="python" and "## Export" in v.code}

