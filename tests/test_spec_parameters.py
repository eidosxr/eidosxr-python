"""Top-level ``parameters`` and ``x-`` extension keys on the Eidos model (EID-190)."""

import json

import pytest
from eidosxr import Document, Eidos, EidosSpecError, TemplateParameter
from pydantic import ValidationError

PARAMETER = {
    "key": "source.dataset",
    "label": "Dataset",
    "kind": "data",
    "targets": ["/data/0/dataSpec"],
    "required": True,
    "default": "oceanum_wave_glob05_era5_v1_grid",
    "dependsOn": "region",
}

EXTENSION = {
    "owner": {"team": "ops", "tags": ["a", None, {"deep": [1, 2.5, None]}]},
    "flag": False,
    "empty": {},
}


def _spec(**extra):
    return {
        "id": "s1",
        "name": "demo",
        "root": {"id": "doc", "nodeType": "document", "content": "hi"},
        **extra,
    }


# --- parameters ----------------------------------------------------------
def test_parameters_typed_round_trip():
    spec = Eidos(
        **_spec(
            parameters=[
                PARAMETER,
                {**PARAMETER, "key": "n", "kind": "number", "default": 3},
            ]
        )
    )
    assert isinstance(spec.parameters[0], TemplateParameter)
    assert spec.parameters[0].kind == "data"
    assert spec.parameters[0].dependsOn == "region"
    dumped = spec.model_dump()
    assert dumped["parameters"][0] == PARAMETER
    assert Eidos.from_json(spec.model_dump_json()).model_dump() == dumped


def test_parameters_omitted_when_unset():
    assert "parameters" not in Eidos(**_spec()).model_dump()


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "colour"},  # not in the enum
        {"key": "Bad-Key"},  # fails the key pattern
        {"key": "k" * 65},  # longer than 64
        {"label": ""},  # shorter than 1
        {"label": "l" * 101},  # longer than 100
        {"targets": []},  # minItems 1
        {"extra": 1},  # additionalProperties false
    ],
)
def test_bad_parameter_rejected(bad):
    with pytest.raises(ValidationError):
        Eidos(**_spec(parameters=[{**PARAMETER, **bad}]))


@pytest.mark.parametrize("missing", ["key", "label", "kind", "targets"])
def test_parameter_required_fields(missing):
    param = {k: v for k, v in PARAMETER.items() if k != missing}
    with pytest.raises(ValidationError):
        Eidos(**_spec(parameters=[param]))


# --- x- extension keys -----------------------------------------------------
def test_extension_keys_round_trip():
    spec = Eidos(**_spec(**{"x-meta": EXTENSION, "x-version": 2}))
    expected = {"x-meta": EXTENSION, "x-version": 2}
    dumped = spec.model_dump()
    assert {k: dumped[k] for k in expected} == expected
    # Nested nulls survive the exclude_none that Eidos.model_dump always applies.
    for out in (
        spec.spec(),
        spec.model_dump(by_alias=True, mode="json"),
        json.loads(spec.model_dump_json(exclude_none=True)),
        json.loads(str(spec)),
    ):
        assert {k: out[k] for k in expected} == expected
    assert Eidos.from_json(spec.model_dump_json()).model_dump() == dumped


def test_null_extension_value_kept():
    spec = Eidos(**_spec(**{"x-cleared": None}))
    assert spec.model_dump()["x-cleared"] is None
    assert json.loads(spec.model_dump_json(exclude_none=True))["x-cleared"] is None
    assert "x-cleared" not in spec.model_dump(exclude={"x-cleared"})


def test_extension_keys_in_html():
    spec = Eidos(**_spec(**{"x-meta": EXTENSION}))
    assert '"x-meta"' in spec.html()


def test_extension_key_edits_are_patched():
    spec = Eidos(**_spec(**{"x-meta": {"a": 1}}))
    setattr(spec, "x-meta", {"a": 2})
    setattr(spec, "x-new", [1])
    assert sorted(spec.patch(), key=lambda op: op["path"]) == [
        {"op": "replace", "path": "/x-meta/a", "value": 2},
        {"op": "add", "path": "/x-new", "value": [1]},
    ]


def test_unknown_key_rejected():
    with pytest.raises(ValidationError) as err:
        Eidos(**_spec(**{"x-ok": 1, "bogus": 1, "xmeta": 2}))
    assert err.value.errors()[0]["type"] == "extra_forbidden"
    assert "bogus, xmeta" in str(err.value)


def test_unknown_attribute_assignment_rejected():
    spec = Eidos(**_spec())
    with pytest.raises(EidosSpecError):
        spec.bogus = 1
    assert "bogus" not in spec.model_dump()


def test_root_schema_fields_still_validated():
    with pytest.raises(ValidationError):
        Eidos(**_spec(id="Not URL safe"))
    spec = Eidos(**_spec(**{"x-meta": 1}))
    spec.root = Document(id="doc2", content="changed")
    assert spec.model_dump()["x-meta"] == 1


def test_parameter_kind_does_not_shadow_common_kind():
    # Star exports: a generated root.Kind would replace common.Kind (valueFrom).
    import eidosxr
    from eidosxr.spec import common, root

    assert eidosxr.Kind is common.Kind
    assert eidosxr.ParameterKind is root.ParameterKind
    assert {k.value for k in eidosxr.ParameterKind} == {
        "data",
        "datakey",
        "text",
        "number",
    }
