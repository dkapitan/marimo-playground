import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    from fsspec.implementations.github import GithubFileSystem

    ROOT = mo.notebook_dir().parent

    ORG, REPO = "dkapitan", "marimo-playground"
    fs = GithubFileSystem(ORG, REPO)
    return ROOT, fs


@app.cell
def _(mo):
    mo.md(r"""
    ## Test with penguins.csv
    """)
    return


@app.cell
def _(ROOT, fs):
    csv_file = "notebooks/public/penguins.csv"
    of = fs.open(csv_file, "rt")
    with of as f:
        csv_fsspec = f.read()

    with open(ROOT / csv_file, "rt") as f:
        csv_local = f.read()
    return csv_fsspec, csv_local


@app.cell
def _(csv_fsspec, csv_local):
    assert csv_local == csv_fsspec
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
