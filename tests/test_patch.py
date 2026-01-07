import pytest
from oceanum.eidos import Eidos, Document


@pytest.fixture
def basic_spec():
    root_node = Document(id="test", content="test")
    eidos = Eidos(
        id="test", name="test", description="I am an EIDOS spec", data=[], root=root_node
    )
    return eidos


def test_basic_patch(basic_spec):
    eidos = basic_spec
    eidos.root.id = "new_name"
    del eidos.description
    patch = eidos.diff()
    assert patch is not None
