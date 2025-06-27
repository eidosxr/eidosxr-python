import pytest
from eidos import Eidos, Node, DocumentView


@pytest.fixture
def basic_spec():
    doc = DocumentView(content="This is a test document node")
    node = Node(
        id="test",
        nodeType="document",
        nodeSpec=doc,
    )
    eidos = Eidos(
        id="test", name="test", description="I am an EIDOS spec", data=[], root=node
    )
    return eidos


def test_basic_init(basic_spec):
    eidos = basic_spec
    assert eidos is not None
    print("Initialized")


def test_basic_change(basic_spec):
    eidos = basic_spec
    eidos.root.nodeSpec.style = "test"
    eidos.root.id = "new_name"
    del eidos.description
    assert not hasattr(eidos, "description")
    assert eidos.dict()["root"]["id"] == "new_name"


def test_html(basic_spec):
    eidos = basic_spec
    html = eidos.html()
    assert html is not None
    print(html)


def test_show(basic_spec):
    eidos = basic_spec
    assert eidos.show()


def test_json():
    json = {
        "id": "test",
        "name": "test",
        "data": [],
        "root": {
            "id": "test",
            "nodeType": "document",
            "nodeSpec": {"content": "This is a test document node"},
        },
    }
    eidos = Eidos.from_dict(json)
    assert eidos.root.id == "test"
