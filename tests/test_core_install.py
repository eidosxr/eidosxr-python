"""The core install: eidosxr works without the optional data stack.

``pip install eidosxr`` installs no oceanum, pandas, geopandas, xarray, altair
or numpy (they are the ``eidosxr[data]`` extra). These tests check that

- importing eidosxr loads none of them;
- the spec models, the Eidos wrapper, the API client and the exceptions work
  with those libraries made unimportable;
- the data helpers then fail with an ImportError naming the extra;
- every name eidosxr exported before the split (0.12.0) is still exported, and
  ``from eidosxr import *`` binds the same names.

The data stack is blocked in a subprocess by a ``sys.meta_path`` finder, so the
tests also run in the full environment. CI additionally runs the whole suite in
an environment without the extra (see .github/workflows/test.yml).
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from eidosxr._optional import DATA_EXPORTS, INSTALL_HINT, import_optional, is_installed

# The top-level packages of the data extra (numpy comes in with pandas/xarray).
DATA_STACK = ("oceanum", "pandas", "geopandas", "xarray", "altair", "numpy")

# Every public name of the three packages on main before the split (v0.12.0),
# generated with dir() — including names that only leaked out of star imports.
EXPORTED_NAMES: dict[str, list[str]] = json.loads(
    (Path(__file__).parent / "data" / "exported_names_0_12_0.json").read_text()
)


def _blocker(packages: tuple[str, ...] = DATA_STACK) -> str:
    """Code that makes ``packages`` unimportable, as if they were not installed."""
    return textwrap.dedent(
        f"""
        import sys

        BLOCKED = {packages!r}

        class _Block:
            def find_spec(self, name, path=None, target=None):
                top = name.split(".")[0]
                if top in BLOCKED:
                    raise ModuleNotFoundError(f"No module named {{top!r}}", name=top)
                return None

        sys.meta_path.insert(0, _Block())
        """
    )


BLOCKER = _blocker()


def _available(name: str) -> bool:
    """Whether a pre-split name should import here: data names need their package."""
    return name not in DATA_EXPORTS or is_installed(DATA_EXPORTS[name].requires)


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

        # A plain data object is not a valid datasource; nothing is imported.
        from eidosxr import EidosDatasource
        try:
            EidosDatasource("d", {"a": [1]})
        except EidosError as exc:
            assert "Invalid inline data type" in str(exc)
        else:
            raise AssertionError("dict accepted as a datasource")

        # Introspection skips the data names instead of failing on them.
        import inspect, pydoc
        for module in (eidosxr, eidosxr.spec):
            assert not set(dir(module)) & {"OceanQL", "Query", "altair", "oceanql"}
            inspect.getmembers(module)
            pydoc.render_doc(module)
        assert "OceanQL" not in eidosxr.__all__

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
        from eidosxr import EidosChart, isotime
        from eidosxr.api.consistency import check_store_consistency

        zarray = {"shape": [2], "chunks": [2], "dtype": "<i8", "compressor": None}
        store = {
            ".zmetadata": json.dumps({"metadata": {"x/.zarray": zarray}}).encode(),
            "x/0": bytes(16),
        }
        calls = {
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
    unexpected = []
    for name in EXPORTED_NAMES[module]:
        try:
            exec(f"from {module} import {name}", {})
        except ImportError as exc:
            if _available(name) or INSTALL_HINT not in str(exc):
                unexpected.append(f"{name}: {exc}")
        else:
            if not _available(name):
                unexpected.append(f"{name} imported without its package")
    assert not unexpected
    expected = {n for n in EXPORTED_NAMES[module] if _available(n)}
    assert expected <= set(dir(importlib.import_module(module)))


def test_star_import_binds_the_same_names():
    """``from eidosxr import *`` binds every pre-split name that can import here.

    ``from eidosxr.spec import *`` binds all but the data names, which it never
    resolves (eidosxr star-imports it, so it must stay light).
    """
    namespace: dict = {}
    exec("from eidosxr import *", namespace)
    expected = {n for n in EXPORTED_NAMES["eidosxr"] if _available(n)}
    assert expected <= set(namespace)

    namespace = {}
    exec("from eidosxr.spec import *", namespace)
    expected = set(EXPORTED_NAMES["eidosxr.spec"]) - set(DATA_EXPORTS)
    assert expected <= set(namespace)


def test_datasource_imports_only_what_it_needs():
    """A DataFrame without xarray names the extra; nothing else is imported."""
    if not is_installed("pandas"):
        pytest.skip("needs pandas")
    code = _blocker(("xarray", "geopandas", "oceanum")) + textwrap.dedent(
        """
        import pandas as pd
        from eidosxr import EidosDatasource
        try:
            EidosDatasource("d", pd.DataFrame({"a": [1, 2]}))
        except ImportError as exc:
            print(str(exc))
        """
    )
    message = _run(code)
    assert "xarray" in message and INSTALL_HINT in message


def test_import_optional_keeps_unrelated_errors(tmp_path, monkeypatch):
    """Only a missing package gets the install hint; a broken one is re-raised."""
    (tmp_path / "eidosxr_broken_pkg").mkdir()
    (tmp_path / "eidosxr_broken_pkg" / "__init__.py").write_text(
        "import eidosxr_no_such_dependency\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    with pytest.raises(ImportError) as missing:
        import_optional("eidosxr_no_such_pkg")
    assert INSTALL_HINT in str(missing.value)

    with pytest.raises(ImportError) as broken:
        import_optional("eidosxr_broken_pkg")
    assert INSTALL_HINT not in str(broken.value)
    assert broken.value.name == "eidosxr_no_such_dependency"


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
    assert expected  # the snapshot does contain data names
    assert set(failed) == expected
    assert all(INSTALL_HINT in message for message in failed.values()), failed
