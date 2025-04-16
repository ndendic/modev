import marimo

__generated_with = "0.12.8"
app = marimo.App(width="medium")


@app.cell
def _():
    #| default_exp core_feature
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md(r"""# This is the example of the core file""")
    return


@app.cell
def hello():
    #| export
    def hello(name="there") -> str:
        return f"Hello, {name} from modev!!!"
    return (hello,)


@app.cell
def _(hello):
    #| export 

    name = "Nikola"
    last = "Dendic"

    hello(name=f"{name} {last}")
    return last, name


@app.cell
def _():
    #| export 
    import modev.cli as cli
    return (cli,)


@app.cell
def _():
    #| export 
    print("Somthing really non sense")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
