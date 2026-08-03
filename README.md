# eidosxr

Python bindings and API client for [EIDOS](https://github.com/eidosxr) — a declarative visualization framework for oceanic and geospatial data applications.

EIDOS applications are defined entirely as JSON specifications. This package lets you create, edit, render and manage those specifications from Python:

- **Typed spec models** — Pydantic models generated from the EIDOS JSON schemas, covering the full specification: world maps, plots, grids, documents, menus, world layers, data sources and theming.
- **Pythonic data binding** — build EIDOS data sources directly from pandas `DataFrame`, geopandas `GeoDataFrame`, xarray `Dataset` objects or Oceanum Datamesh queries.
- **Altair charts** — use [Altair](https://altair-viz.github.io/) charts as plot specifications.
- **Change tracking** — every `Eidos` model tracks edits and can emit an RFC 6902 JSON Patch of the changes since the last checkpoint.
- **Platform API client** — `EidosConnection` for the EIDOS platform: specification and template CRUD, JSON-Patch updates with optimistic concurrency, zarr dataset ingestion and asset storage.

## Installation

```shell
pip install eidosxr
```

Requires Python 3.9+.

> This package was previously published as `oceanum.eidos` (repo `oceanum-io/eidos-python`). Update imports from `from oceanum.eidos import ...` to `from eidosxr import ...`.

## Quickstart

Build a specification from an Altair chart and open it in a browser:

```python
import altair as alt
import pandas as pd

from eidosxr import Eidos, EidosChart, Plot

cars = pd.read_json("https://vega.github.io/vega-datasets/data/cars.json")
chart = (
    alt.Chart(cars)
    .mark_point()
    .encode(x="Horsepower", y="Miles_per_Gallon", color="Origin")
)

spec = Eidos(
    id="cars-demo",
    name="Cars demo",
    data=[],
    root=Plot(id="plot", plotSpec=EidosChart(chart)),
)

print(spec)        # the JSON specification
html = spec.html() # standalone HTML page using the hosted EIDOS renderer
spec.show()        # write a temp HTML file and open it in a browser
```

The specification is the single source of truth: every attribute is a typed Pydantic field validated against the EIDOS schema, and `spec.model_dump()` / `str(spec)` produce the JSON document consumed by the EIDOS runtime.

### Data sources

`EidosDatasource` converts Python data objects into inline EIDOS data sources for the root-level `data` field:

| Input type | EIDOS data type |
| --- | --- |
| `pandas.DataFrame` | `dataset` (converted via xarray) |
| `xarray.Dataset` | `dataset` |
| `geopandas.GeoDataFrame` | `geojson` |
| `oceanum.datamesh.Query` | `oceanumDatamesh` (fetched by the renderer at load time) |

```python
from eidosxr import EidosDatasource

ds = EidosDatasource("waves", dataframe, coordkeys={"t": "time"})
```

Reference a data source from an Altair chart by passing named data with the datasource id, e.g. `alt.Chart(alt.NamedData(name="waves"))`, wrapped with `EidosChart`.

### Node types

The view hierarchy is composed of typed nodes, all importable from `eidosxr`: `World` (maps with world layers: feature, gridded, label, scenegraph, seasurface, track, wmts), `Plot` (Vega-Lite charts), `Grid` and `Menu` (layout), and `Document` (rich text/markdown content).

### Change tracking and JSON Patch

An `Eidos` model checkpoints its state on construction, and edits are validated against the schema on assignment (invalid values raise `EidosSpecError`). `spec.patch()` returns the RFC 6902 JSON Patch of everything changed since the last checkpoint — and advances the checkpoint, so call it exactly once per update cycle.

```python
spec.name = "Cars demo v2"
spec.patch()
# [{"op": "replace", "path": "/name", "value": "Cars demo v2"}]
```

## Platform API client

`EidosConnection` is a typed client for the EIDOS platform API (`https://api.eidosxr.com`). It authenticates with a bearer token — a platform user JWT or an `ek_` Oceanum API key.

```python
from eidosxr import EidosConnection

conn = EidosConnection(token="ek_...")  # or set EIDOS_TOKEN

# List and fetch specifications
specs = conn.list_specifications()
record = conn.get_specification("my-spec")  # -> Specification (carries .version)
spec = record.to_eidos()                    # -> live Eidos model

# Edit the model, then push the diff as a JSON Patch with optimistic locking
spec.name = "Updated name"
conn.update_specification("my-spec", spec, if_match=record.version)
```

`update_specification` sends only the model's computed patch with an `If-Match` header. On a version conflict the client raises `PreconditionFailed` (carrying the server's `current_version`); other mapped errors include `NotFound`, `PatchConflict` and the base `EidosError`.

The client also covers:

- **Templates** — `list_templates`, `create_template`, `create_template_from_node`, `update_template`, `archive_template`, `delete_template`.
- **Datasets (zarr ingestion)** — `create_empty_dataset`, `put_zarr_object` (max 64 MB per object), `finalize_dataset`, `get_dataset_metadata`, `get_zarr_object`, plus consistency checks via `check_put_consistency`.
- **Assets** — `upload_asset`, `get_asset`.

Dataset and asset calls require the ingestion service URL (`ingestion_service` argument or `EIDOS_INGESTION_SERVICE`).

### Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `EIDOS_TOKEN` | Bearer token for `EidosConnection` | — |
| `EIDOS_SERVICE` | Spec API base URL | `https://api.eidosxr.com` |
| `EIDOS_INGESTION_SERVICE` | Zarr ingestion service base URL | — |
| `EIDOS_RENDERER` | Renderer used by `html()` / `show()` | `https://render.eidos.oceanum.io/v<major>.<minor>` |

## Development

```shell
git clone git@github.com:eidosxr/eidosxr-python.git
cd eidosxr-python
pip install -e ".[test]"
pytest
```

Most model modules (`root.py`, `data.py`, `common.py`, `panel.py`, `theme.py`, `geojson.py`, the `node/` package) are **generated** from the EIDOS JSON schemas with [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) — do not edit them by hand. Regenerate with:

```shell
pip install -e ".[development]"
./autogen/gen_models.sh
```

The package version tracks the EIDOS specification version the models were generated from.

## License

[MIT](LICENSE)
