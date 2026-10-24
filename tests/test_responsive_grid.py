"""Grid `responsive` overrides, menu `position` and world `maxPixelRatio` (EIDOS v0.12)."""

import json

import pytest

from eidosxr import Grid, GridSize, Menu, MenuLayoutItem, Nested, ResponsiveItem

CHILDREN = [
    Nested(id="a", children=[]),
    Nested(id="b", children=[]),
]


def test_grid_responsive_round_trips() -> None:
    grid = Grid(
        id="g",
        gridSize=GridSize(columns=2, rows=1),
        children=CHILDREN,
        responsive=[
            ResponsiveItem(
                maxWidth=600,
                gridSize=GridSize(columns=1, rows=2),
                gridLayout=[
                    {"x": 0, "y": 0, "w": 1, "h": 1},
                    {"x": 0, "y": 1, "w": 1, "h": 1},
                ],
            ),
            {"maxWidth": 1000, "gridSize": {"columns": 2, "rows": 2}},
        ],
    )
    spec = json.loads(grid.model_dump_json(exclude_none=True))
    assert spec["responsive"] == [
        {
            "maxWidth": 600,
            "gridSize": {"columns": 1, "rows": 2},
            "gridLayout": [
                {"x": 0, "y": 0, "w": 1, "h": 1},
                {"x": 0, "y": 1, "w": 1, "h": 1},
            ],
        },
        {"maxWidth": 1000, "gridSize": {"columns": 2, "rows": 2}},
    ]


@pytest.mark.parametrize(
    "entry", [{"maxWidth": 0}, {}, {"maxWidth": 600, "columns": 1}]
)
def test_grid_responsive_rejects_invalid_entries(entry: dict) -> None:
    with pytest.raises(ValueError):
        Grid(
            id="g",
            gridSize=GridSize(columns=1, rows=1),
            children=CHILDREN,
            responsive=[entry],
        )


def test_menu_position_has_no_default() -> None:
    # Unset means "top" in the renderer, but the field carries no default so a
    # serialised spec doesn't override the legacy `layout` field.
    menu = Menu(
        id="m",
        menuLayout=[MenuLayoutItem(label="A"), MenuLayoutItem(label="B")],
        children=CHILDREN,
    )
    assert menu.position is None
    assert "position" not in json.loads(menu.model_dump_json(exclude_none=True))
    assert Menu(id="m", menuLayout=[], children=[], position="left").position == "left"


def test_world_max_pixel_ratio_defaults_to_two() -> None:
    assert Nested(id="w", children=[]).maxPixelRatio == 2
