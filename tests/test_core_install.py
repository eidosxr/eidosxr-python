"""The core install: eidosxr works without the optional data stack.

``pip install eidosxr`` installs no oceanum, pandas, geopandas, xarray, altair
or numpy (they are the ``eidosxr[data]`` extra). These tests check that

- importing eidosxr loads none of them;
- the spec models, the Eidos wrapper, the API client and the exceptions work
  with those libraries made unimportable;
- the data helpers then fail with an ImportError naming the extra;
- every name eidosxr exported before the split (0.12.0) is still exported.

The data stack is blocked in a subprocess by a ``sys.meta_path`` finder, so the
tests also run in the full environment. CI additionally runs the whole suite in
an environment without the extra (see .github/workflows/test.yml).
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from eidosxr._optional import DATA_EXPORTS, INSTALL_HINT

# The top-level packages of the data extra (numpy comes in with pandas/xarray).
DATA_STACK = ("oceanum", "pandas", "geopandas", "xarray", "altair", "numpy")

# Every public name of the three packages on main before the split (v0.12.0),
# generated with dir() — including names that only leaked out of star imports.
EXPORTED_NAMES: dict[str, list[str]] = json.loads(
    (Path(__file__).parent / "data" / "exported_names_0_12_0.json").read_text()
)

BLOCKER = textwrap.dedent(
    f"""
    import sys

    BLOCKED = {DATA_STACK!r}

    class _BlockDataStack:
        # Makes the data extra unimportable, as in a core-only install.
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise ImportError(f"{{name}} is blocked (core-only test)")
            return None

    sys.meta_path.insert(0, _BlockDataStack())
    """
)


def _data_extra_installed() -> bool:
    return all(importlib.util.find_spec(m) is not None for m in DATA_STACK)


def _run(code: str) -> str:
    """Run ``code`` in a fresh interpreter; return its stdout, failing on error.

    The child imports the same eidosxr as this test process (a source checkout
    or the installed package), whatever the working directory.
    """
    import eidosxr

    source = str(Path(eidosxr.__file__).resolve().parent.parent)
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            p for p in (source, os.environ.get("PYTHONPATH")) if p
        ),
    }
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=300,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


def test_import_loads_no_data_stack():
    """In the normal environment, importing eidosxr loads none of the data stack."""
    out = _run(
        "import json, sys\n"
        "import eidosxr, eidosxr.api, eidosxr.spec\n"
        "import eidosxr.api.consistency, eidosxr.spec.base, eidosxr.spec.vegaspec\n"
        f"print(json.dumps(sorted(m for m in sys.modules "
        f"if m.split('.')[0] in {DATA_STACK!r})))"
    )
    assert json.loads(out) == []


def test_core_without_data_stack():
    """Typical client use works with the data stack unimportable."""
    code = BLOCKER + textwrap.dedent(
        """
        import eidosxr, eidosxr.api, eidosxr.spec
        from eidosxr import Document, Eidos, Plot, TopLevelSpec, World
        from eidosxr.api import (
            EidosApiError, EidosConnection, EidosError, NotFound, PreconditionFailed,
        )
        from eidosxr.api.consistency import ConsistencyError, load_consolidated_metadata
        from eidosxr.spec import EidosSpecError
        import responses

        # Spec models, the Eidos wrapper and JSON patches.
        spec = Eidos(
            id="s1", name="demo", data=[], root=Document(id="root", content="hello")
        )
        spec.root.content = "updated"
        patch = spec.patch()
        assert patch == [{"op": "replace", "path": "/root/content", "value": "updated"}]
        assert Eidos.from_json(str(spec)).model_dump() == spec.model_dump()
        assert "updated" in spec.html()
        plot = Plot(id="p", plotSpec={"mark": "point"})
        assert plot.plotSpec.root == {"mark": "point"}
        assert TopLevelSpec('{"mark": "bar"}').root == {"mark": "bar"}
        try:
            spec.root.nodeType = "not-a-node"
        except EidosSpecError:
            pass
        else:
            raise AssertionError("invalid edit was accepted")

        # The API client, against a mocked service.
        SERVICE = "https://api.example"
        body = {
            "id": "s1", "name": "demo", "description": None, "account_id": None,
            "is_public": False, "spec": spec.model_dump(),
            "created_at": "t", "updated_at": "t", "version": 3,
        }
        conn = EidosConnection(token="ek_test", service=SERVICE)
        with responses.RequestsMock() as mock:
            mock.get(f"{SERVICE}/specifications/s1", json=body)
            mock.patch(
                f"{SERVICE}/specifications/s1",
                json={"id": "s1", "spec": {}, "version": 4, "updated_at": "t"},
            )
            mock.get(f"{SERVICE}/specifications/nope", status=404, json={"error": "x"})
            record = conn.get_specification("s1")
            model = record.to_eidos()
            model.name = "renamed"
            assert conn.update_specification("s1", model, if_match=3).version == 4
            sent = mock.calls[1].request
            assert sent.headers["If-Match"] == '"3"'
            assert sent.body == b'[{"op": "replace", "path": "/name", "value": "renamed"}]'
            try:
                conn.get_specification("nope")
            except NotFound as exc:
                assert isinstance(exc, EidosApiError) and isinstance(exc, EidosError)
            else:
                raise AssertionError("404 did not raise NotFound")
        assert issubclass(PreconditionFailed, EidosApiError)
        assert issubclass(ConsistencyError, EidosError)
        assert load_consolidated_metadata(lambda key: b'{"metadata": {}}') == {}

        assert not [m for m in sys.modules if m.split(".")[0] in BLOCKED]
        print("ok")
        """
    )
    assert _run(code).strip() == "ok"


def test_data_helpers_name_the_extra():
    """Without the data stack, the data helpers raise an ImportError naming the extra."""
    code = BLOCKER + textwrap.dedent(
        """
        import json
        import eidosxr, eidosxr.spec
        from eidosxr import EidosChart, EidosDatasource, isotime
        from eidosxr.api.consistency import check_store_consistency

        zarray = {"shape": [2], "chunks": [2], "dtype": "<i8", "compressor": None}
        store = {
            ".zmetadata": json.dumps({"metadata": {"x/.zarray": zarray}}).encode(),
            "x/0": bytes(16),
        }
        calls = {
            "EidosDatasource": lambda: EidosDatasource("d", {"a": [1]}),
            "EidosChart": lambda: EidosChart({"mark": "point"}),
            "isotime": lambda: isotime("2026-01-01"),
            "check_store_consistency": lambda: check_store_consistency(store),
            "from eidosxr import OceanQL": lambda: exec("from eidosxr import OceanQL"),
            "from eidosxr.spec import OceanQL": (
                lambda: exec("from eidosxr.spec import OceanQL")
            ),
            "eidosxr.Query": lambda: eidosxr.Query,
            "eidosxr.spec.altair": lambda: eidosxr.spec.altair,
            "import eidosxr.spec.oceanql": lambda: exec("import eidosxr.spec.oceanql"),
        }
        messages = {}
        for label, call in calls.items():
            try:
                call()
            except ImportError as exc:
                messages[label] = str(exc)
            else:
                messages[label] = None
        print(json.dumps(messages))
        """
    )
    messages = json.loads(_run(code))
    for label, message in messages.items():
        assert message is not None, f"{label} did not raise ImportError"
        assert INSTALL_HINT in message, f"{label}: {message}"


def test_unknown_attribute_is_attribute_error():
    import eidosxr
    import eidosxr.spec

    for module in (eidosxr, eidosxr.spec):
        with pytest.raises(AttributeError):
            module.not_a_name
        assert not hasattr(module, "not_a_name")


@pytest.mark.parametrize("module", sorted(EXPORTED_NAMES))
def test_exported_names_still_import(module: str):
    """``from <module> import X`` works for every name exported before the split.

    Without the data extra, the data names raise an ImportError naming it.
    """
    full = _data_extra_installed()
    missing, wrong_error = [], []
    for name in EXPORTED_NAMES[module]:
        try:
            exec(f"from {module} import {name}", {})
        except ImportError as exc:
            if full or name not in DATA_EXPORTS or INSTALL_HINT not in str(exc):
                wrong_error.append(f"{name}: {exc}")
        else:
            if not full and name in DATA_EXPORTS:
                missing.append(f"{name} imported without the data extra")
    assert not missing and not wrong_error, missing + wrong_error
    assert set(EXPORTED_NAMES[module]) <= set(dir(importlib.import_module(module)))


def test_exported_names_without_data_stack():
    """The same check with the data stack blocked: only DATA_EXPORTS may fail."""
    code = BLOCKER + textwrap.dedent(
        f"""
        import json
        names = {EXPORTED_NAMES!r}
        failed = {{}}
        for module, module_names in names.items():
            for name in module_names:
                try:
                    exec(f"from {{module}} import {{name}}", {{}})
                except ImportError as exc:
                    failed[f"{{module}}.{{name}}"] = str(exc)
        print(json.dumps(failed))
        """
    )
    failed = json.loads(_run(code))
    expected = {
        f"{module}.{name}"
        for module, names in EXPORTED_NAMES.items()
        for name in names
        if name in DATA_EXPORTS
    }
    assert set(failed) == expected
    assert all(INSTALL_HINT in message for message in failed.values()), failed
