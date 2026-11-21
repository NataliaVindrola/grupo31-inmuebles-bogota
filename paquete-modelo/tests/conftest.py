import pytest

from modelo_inmuebles.config.core import TRAINED_DIR
from modelo_inmuebles import __version__


@pytest.fixture(scope="session")
def version():
    return __version__


@pytest.fixture(scope="session")
def dir_modelos():
    return TRAINED_DIR
