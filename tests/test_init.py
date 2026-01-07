import pytest
from oceanum.eidos import Eidos, Document


@pytest.fixture
def basic_spec():
    root_node = Document(id="test", content="This is a test document node")
    eidos = Eidos(
        id="test", name="test", description="I am an EIDOS spec", data=[], root=root_node
    )
    return eidos


def test_basic_init(basic_spec):
    eidos = basic_spec
    assert eidos is not None
    print("Initialized")


def test_basic_change(basic_spec):
    eidos = basic_spec
    eidos.root.id = "new_name"
    del eidos.description
    assert not hasattr(eidos, "description")
    assert eidos.model_dump()["root"]["id"] == "new_name"


def test_html(basic_spec):
    eidos = basic_spec
    html = eidos.html()
    assert html is not None
    print(html)


def test_show(basic_spec):
    eidos = basic_spec
    assert eidos.show()


def test_json():
    json_spec = {
        "id": "test",
        "name": "test",
        "data": [],
        "root": {
            "id": "test",
            "content": "This is a test document node",
        },
    }
    eidos = Eidos.from_dict(json_spec)
    assert eidos.root.id == "test"
