import pytest
from eidos import Eidos, Node, DocumentView, Particles


@pytest.fixture
def basic_spec():
    doc = DocumentView(content="test")
    node = Node(
        id="test",
        nodeType="document",
        nodeSpec=doc,
    )
    eidos = Eidos(
        id="test", name="test", description="I am an EIDOS spec", data=[], root=node
    )
    return eidos


def test_basic_patch(basic_spec):
    eidos = basic_spec
    eidos.root.nodeSpec.style = "test"
    eidos.root.id = "new_name"
    del eidos.description
    patch = eidos.diff()
    assert patch is not None
