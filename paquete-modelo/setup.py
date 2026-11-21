#!/usr/bin/env python
from pathlib import Path

from setuptools import find_packages, setup

NAME = "modelo-inmuebles-bogota"
DESCRIPTION = "Modelos de rango del valor y de reventa a 3 años de compraventas en Bogotá (Grupo 31, MIAD)."
AUTHOR = "Grupo 31 - MIAD Universidad de los Andes"
REQUIRES_PYTHON = ">=3.11"

ROOT_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = ROOT_DIR / "modelo_inmuebles"
about = {"__version__": (PACKAGE_DIR / "VERSION").read_text(encoding="utf-8").strip()}


def list_reqs(fname: str = "requirements.txt") -> list[str]:
    lines = (ROOT_DIR / "requirements" / fname).read_text(encoding="utf-8").splitlines()
    return [l.strip() for l in lines if l.strip() and not l.startswith(("#", "-r"))]


setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=(ROOT_DIR / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author=AUTHOR,
    python_requires=REQUIRES_PYTHON,
    packages=find_packages(exclude=("tests",)),
    package_data={"modelo_inmuebles": ["VERSION", "config.yml", "trained/*/*/*.joblib", "trained/*/*/*.json"]},
    install_requires=list_reqs(),
    extras_require={"train": ["mlflow>=3.0"]},
    include_package_data=True,
    license="BSD-3",
    classifiers=["Programming Language :: Python :: 3", "Programming Language :: Python :: 3.12",
                 "Programming Language :: Python :: 3.13"],
)
