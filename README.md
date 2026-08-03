# eidosxr

Python bindings and API client for [EIDOS](https://github.com/eidosxr/eidos) —
the declarative visualisation framework for oceanic, geospatial and immersive
data applications. Create, edit, render and manage EIDOS specifications from
Python, and drive the EIDOS platform API.

> This package supersedes the earlier `oceanum.eidos` / `eidos-python`
> package. Import from `eidosxr` instead of `oceanum.eidos`.

## Installation

```bash
pip install eidosxr
```

Requires Python ≥ 3.9.

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

`EidosDatasource` wraps your data for the spec's `data` block. It accepts a
pandas `DataFrame` or an xarray `Dataset` (inline dataset), a geopandas
`GeoDataFrame` (GeoJSON), or an [Oceanum Datamesh](https://docs.oceanum.io)
`Query` (fetched server-side by the renderer):

```python
import pandas as pd
from eidosxr import EidosDatasource

df = pd.DataFrame({"x": [0.0, 1.0, 2.0], "v": [3.1, 2.7, 4.2]})
ds = EidosDatasource("profile", df)     # dataType == "dataset"
```

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

The models in `eidosxr/spec/` are generated. From a checkout of the
[eidos monorepo](https://github.com/eidosxr/eidos) (this repo is its
`bindings/python` submodule, and the script reads the schemas and version
from the parent checkout):

```bash
bash autogen/gen_models.sh
```

Requires `datamodel-code-generator` and `node`. The script writes the spec
tree only — `eidosxr/__init__.py` and `eidosxr/api/__init__.py` are
hand-maintained.

## Tests

```bash
pip install -e . responses
pytest tests/
```

## Licence

MIT — see [LICENSE](LICENSE).
