import tempfile

import nox

nox.options.sessions = "lint", "test"
locations = "src", "tests", "noxfile.py"


def install_with_constraints(session, *args, **kwargs):
    with tempfile.NamedTemporaryFile() as requirements:
        session.run(
            "poetry",
            "export",
            "--format=requirements.txt",
            f"--output={requirements.name}",
            external=True,
        )
        session.install(f"--constraint={requirements.name}", *args, **kwargs)


@nox.session(python=["3.8"])
def test(session):
    args = session.posargs or ["--cov"]
    install_with_constraints(session, "coverage[toml]", "pytest", "pytest-cov")
    session.run("pytest", *args)


@nox.session(python="3.8")
def lint(session):
    args = session.posargs or locations
    install_with_constraints(session, "flake8", "flake8-black", "flake8-import-order")
    session.run("flake8", *args)


@nox.session(python="3.8")
def format(session):
    args = session.posargs or locations
    install_with_constraints(session, "black")
    session.run("black", *args)
