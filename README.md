# eidosxr

Python bindings and API client for [EIDOS](https://github.com/eidosxr/eidos) —
the declarative visualisation framework for oceanic, geospatial and immersive
data applications. Create, edit, render and manage EIDOS specifications from
Python, and drive the EIDOS platform API.

> This package supersedes the earlier `oceanum.eidos` / `eidos-python`
> package. Import from `eidosxr` instead of `oceanum.eidos`.

## Installation

```bash
pip install eidosxr            # core: spec models + platform API client
pip install 'eidosxr[data]'    # + the data helpers (pandas, xarray, Datamesh, Altair)
pip install 'eidosxr[all]'     # everything (currently the same as [data])
```

Requires Python ≥ 3.10.

| Install | Pulls in | What works |
| --- | --- | --- |
| `eidosxr` | pydantic, requests, jsonpatch, jinja2 | the spec models (`eidosxr.spec`), `Eidos` (edit, diff/patch, `html()`, `show()`), the API client (`eidosxr.api`: `EidosConnection`, response models, exceptions) |
| `eidosxr[data]` | + oceanum, pandas, geopandas, xarray, altair, numpy | also `EidosDatasource`, `EidosChart`, `isotime`, `OceanQL` and the zarr consistency checks (`check_store_consistency`, `compare_stores`, `EidosConnection.check_put_consistency`) |

The core install is small (about 16 MB of site-packages, against about 770 MB
with `[data]`). Importing `eidosxr` never loads the data stack: the data
helpers import it when called. Without the extra they raise an `ImportError`
that says to `pip install 'eidosxr[data]'`.

> **Upgrading to 0.12.1.** Up to 0.12.0, `pip install eidosxr` installed the
> data stack too. From 0.12.1 it is the `data` extra, so if you use
> `EidosDatasource`, `EidosChart`, `isotime`, `OceanQL` or the zarr consistency
> checks, install `eidosxr[data]` (or depend on it in your requirements). The
> schema and the public names are unchanged: `from eidosxr import X` still
> works for every name exported before.

## Package layout

- **`eidosxr.spec`** — the EIDOS specification models: pydantic models
  generated from the [EIDOS JSON schemas](https://schemas.oceanum.io/eidos)
  (world, plot, document and grid nodes, world layers, data, theme, …) plus
  the live `Eidos` wrapper class and the spec-side exceptions.
- **`eidosxr.api`** — the EIDOS platform API client: `EidosConnection`,
  the response models, zarr consistency checks and the HTTP error hierarchy.

Everything public is also re-exported at the top level, so
`from eidosxr import Eidos, World, EidosConnection` works.

## Quickstart — build and display a spec

```python
from eidosxr import Eidos, Document

spec = Eidos(
    id="demo",
    name="demo",
    description="I am an EIDOS spec",
    data=[],
    root=Document(id="doc-1", content="Hello EIDOS"),
)

spec.show()          # open in a browser via the hosted renderer
html = spec.html()   # or get the embeddable HTML (e.g. for notebooks)
```

The models validate on assignment — invalid edits raise `EidosSpecError`
immediately:

```python
spec.root.content = "Updated"        # fine
spec.root.nodeType = "not-a-node"    # raises EidosSpecError
```

An `Eidos` model tracks its own changes: `spec.diff()` returns the RFC-6902
JSON Patch since the last checkpoint, and `spec.patch()` returns it and
advances the checkpoint. `Eidos.from_dict(...)` / `Eidos.from_json(...)` load
existing specifications.

## Data binding

Needs the data extra: `pip install 'eidosxr[data]'`.

`EidosDatasource` wraps your data for the spec's `data` block. It accepts a
pandas `DataFrame` or an xarray `Dataset` (inline dataset), a geopandas
`GeoDataFrame` (GeoJSON), or an [Oceanum Datamesh](https://docs.oceanum.io)
`Query` (fetched server-side by the renderer):

```python
import pandas as pd
from oceanum.datamesh import Query
from eidosxr import EidosDatasource

df = pd.DataFrame({"time": pd.date_range("2021-01-01", periods=3), "v": [3.1, 2.7, 4.2]})
inline = EidosDatasource("profile", df)   # dataType == "dataset"

remote = EidosDatasource(                 # dataType == "oceanql"
    "waves", Query(datasource="oceanum_wave_glob05_era5_v1_grid")
)
```

Datetime columns are serialised to ISO 8601 strings, which the renderer
normalises back to times.

## Platform API client

`EidosConnection` talks to the EIDOS platform (specification and template
CRUD, JSON-Patch updates, zarr dataset and asset storage). It authenticates
with a bearer token — an `ek_` Oceanum API key or a Supabase user JWT —
passed as `token=` or via the `EIDOS_TOKEN` environment variable.

```python
from eidosxr.api import EidosConnection

conn = EidosConnection(token="ek_...")

record = conn.get_specification(spec_id)   # -> Specification (has .version)
spec = record.to_eidos()                   # -> live Eidos model
spec.root.title = "Updated"
conn.update_specification(spec_id, spec, if_match=record.version)
```

Failed requests raise typed exceptions from `eidosxr.api` — for example
`NotFound` (404), `PreconditionFailed` (412, carries `.current_version`) or
`QuotaExceeded` (402) — all subclasses of `EidosApiError`, which is itself an
`EidosError`.

## Regenerating the models (development)

The models in `eidosxr/spec/` are generated from the EIDOS JSON schemas. Pass
the schema version; the script reads that version's published path,
`https://schemas.oceanum.io/eidos/v0.12/`:

```bash
pip install -e '.[development]'
bash autogen/gen_models.sh v0.12
```

To generate from schemas that are not published yet, give the local copy of
that path as a second argument, e.g. from a checkout of the
[eidos monorepo](https://github.com/eidosxr/eidos):

```bash
bash autogen/gen_models.sh v0.12 ../eidos/packages/schemas/src/eidos
```

The script stops if the schemas are not the version asked for, if
`datamodel-codegen` is not the pinned version, or if anything fails.
`datamodel-code-generator` is pinned in the `development` extra: its output
differs materially between versions, and current releases cannot process
`node/world.json`. The script writes the spec tree only —
`eidosxr/__init__.py`, `eidosxr/api/__init__.py` and `eidosxr/version.py` are
hand-maintained. `autogen/gen_init.py` writes `eidosxr/spec/__init__.py`; it
leaves the modules that need the data extra (`oceanql.py`) out of the star
imports and resolves their names lazily instead. Run the tests afterwards; `tests/test_nested_world.py` guards
against the generator dropping a nested world's view state.

## Tests

```bash
pip install -e '.[all,test]'
pytest tests/
```

With only `pip install -e '.[test]'` (the core install) the data-helper tests
are skipped; `tests/test_core_install.py` checks the core works without the
data stack. CI runs both.

## Licence

MIT — see [LICENSE](LICENSE).
