import marimo

__generated_with = "0.12.8"
app = marimo.App(width="medium")

@app.cell
def _():
    #| default_exp simple
    return

@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def super_simple():
    #| export
    def super_simple():
        print("Oh, this was so super simple..")
    return (super_simple,)


if __name__ == "__main__":
    app.run()
