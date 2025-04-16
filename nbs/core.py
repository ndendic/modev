import marimo

__generated_with = "0.12.8"
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
    mo.md(r"""# Core""")
    return


@app.cell
def hello():
    #| export
    def hello() -> str:
        return "Hello from modev!"
    return (hello,)


if __name__ == "__main__":
    app.run()
