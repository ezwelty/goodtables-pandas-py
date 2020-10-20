"""Nox sessions."""
import tempfile

import nox

nox.options.sessions = "lint", "test"
locations = "src", "tests", "noxfile.py"


def install_with_constraints(session, *args, **kwargs):
    """
    Install packages constrained by Poetry's lock file.

    This function wraps :meth:`nox.sessions.Session.install`.
    It invokes `pip` to install packages inside of the session's virtualenv,
    pinned to the versions specified in `poetry.lock`.

    Arguments:
        session: Session to install packages into.
        args: Command-line arguments for `pip`.
        kwargs: Additional keyword arguments for :meth:`nox.sessions.Session.install`.
    """
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
    """Test with pytest."""
    args = session.posargs or ["--cov"]
    install_with_constraints(session, "coverage[toml]", "pytest", "pytest-cov")
    session.run("pytest", *args)


@nox.session(python="3.8")
def lint(session):
    """Lint with flake8."""
    args = session.posargs or locations
    # install_with_constraints(
    #     session,
    #     "flake8",
    #     "flake8-black",
    #     "flake8-docstrings",
    #     "flake8-import-order"
    # )
    session.run("poetry", "install", external=True)
    session.run("flake8", *args)


@nox.session(python="3.8")
def format(session):
    """Format with black."""
    args = session.posargs or locations
    install_with_constraints(session, "black")
    session.run("black", *args)
