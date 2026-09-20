"""A world nested in a grid, menu or panel keeps its full view state."""

import json
import warnings

import pytest

from eidosxr import Grid, GridSize, Nested

VIEW = {"longitude": -171.55, "latitude": -7.75, "zoom": 2.4}


def nested(**view: object) -> Nested:
    return Nested(id="map", children=[], viewState={**VIEW, **view})


def test_nested_world_keeps_its_view_state_through_a_grid() -> None:
    # Nested.viewState was generated as a model holding only viewType, so a
    # world inside a grid silently lost its centre and zoom and serialised
    # viewState as {}, which the schema rejects.
    grid = Grid(id="g", gridSize=GridSize(columns=1, rows=1), children=[nested()])
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # no pydantic serialiser fallback either
        spec = json.loads(grid.model_dump_json(exclude_none=True))
    view = spec["children"][0]["viewState"]
    assert {key: view[key] for key in VIEW} == VIEW


@pytest.mark.parametrize("view_type", ["map", "globe"])
def test_nested_world_accepts_map_and_globe(view_type: str) -> None:
    assert nested(viewType=view_type).viewState.viewType == view_type


@pytest.mark.parametrize("view_type", ["vr", "fp", "ar"])
def test_nested_world_rejects_the_root_only_view_types(view_type: str) -> None:
    # The immersive views take over the whole viewport, so the schema only
    # allows them on a world that is the root of the specification.
    with pytest.raises(ValueError):
        nested(viewType=view_type)
