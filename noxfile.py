import nox

nox.options.sessions = "lint", "test"


@nox.session(python=["3.8"])
def test(session):
    args = session.posargs or ["--cov"]
    session.run("poetry", "install", external=True)
    session.run("pytest", *args)


@nox.session(python="3.8")
def lint(session):
    args = session.posargs or ("src", "tests", "noxfile.py")
    session.install("flake8", "flake8-black", "flake8-import-order")
    session.run("flake8", *args)


@nox.session(python="3.8")
def format(session):
    args = session.posargs or ("src", "tests", "noxfile.py")
    session.install("black")
    session.run("black", *args)
