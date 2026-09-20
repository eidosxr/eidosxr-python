#!/usr/bin/env bash
# Generate the eidosxr.spec models from the EIDOS JSON schemas.
#
# usage: autogen/gen_models.sh <version> [schema-dir]
#
#   <version>     The EIDOS schema version to generate for: v0.12. The schemas are
#                 read from its version-specific path,
#                 https://schemas.oceanum.io/eidos/<version>/
#   [schema-dir]  Read that path from a local directory instead of downloading it,
#                 e.g. <eidos checkout>/packages/schemas/src/eidos. This is how to
#                 generate from schemas that are not published yet.
#
# Needs datamodel-codegen 0.28.5 (pip install -e '.[development]'), curl, perl
# and python. The generator is pinned because its output differs materially
# between versions, and current releases cannot process node/world.json.
set -euo pipefail

VERSION=${1:-}
SCHEMADIR=${2:-}
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+$ ]]; then
  echo "usage: $0 <version> [schema-dir]    e.g. $0 v0.12" >&2
  exit 2
fi

ROOTDIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." &> /dev/null && pwd)
SCHEMAHOST=https://schemas.oceanum.io
SCHEMAURL=$SCHEMAHOST/eidos/$VERSION

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/node/worldlayer"

if [ -n "$SCHEMADIR" ]; then
  echo "Reading the $VERSION schemas from $SCHEMADIR"
  cp -RL "$SCHEMADIR"/* "$TMP"
  # geojson.json is shared between schema sets, so it sits beside the eidos
  # directory rather than in it.
  cp "$SCHEMADIR/../geojson.json" "$TMP/geojson.json"
else
  echo "Reading the schemas from $SCHEMAURL"
  for schema in root data common panel theme \
    node/plot node/world node/document node/grid node/menu node/derived \
    node/worldlayer/common node/worldlayer/feature node/worldlayer/gridded \
    node/worldlayer/label node/worldlayer/pointcloud node/worldlayer/scenegraph \
    node/worldlayer/seasurface node/worldlayer/track node/worldlayer/wmts; do
    curl -fsS "$SCHEMAURL/$schema.json" -o "$TMP/$schema.json"
  done
  # geojson.json is shared between schema sets, so it is not under the version path.
  curl -fsS "$SCHEMAHOST/geojson.json" -o "$TMP/geojson.json"
fi

# The schemas must be the version asked for: their $ids carry it.
if ! grep -q "\"\$id\": \"$SCHEMAURL/root.json\"" "$TMP/root.json"; then
  echo "root.json is not the $VERSION schema (expected \$id $SCHEMAURL/root.json)" >&2
  exit 1
fi

#Create a stub for the vega-lite schema
echo "{
    \"description\": \"Vega or Vega-Lite specification\",
    \"type\": \"object\",
    \"definitions\": {
        \"TopLevelSpec\": {
            \"title\":\"Vega spec\",
            \"description\": \"Top-level specification of a Vega or Vega-Lite visualization\",
            \"type\": \"object\",
            \"properties\": {
            }
        },
    },

}" > "$TMP/vegaspec.json"

# Replace vega schema reference with a stub
perl -p -i -e "s|https\:\/\/vega\.github\.io\/schema\/vega-lite\/v6.json|$TMP/vegaspec.json#/definitions/TopLevelSpec|g" "$TMP/node/plot.json"

# Resolve circular dependency by removing menu node from grid
perl -p -i -e "s|menu.json|document.json|g" "$TMP/node/grid.json"



datamodel-codegen --input-file-type jsonschema --input "$TMP" --output "$ROOTDIR/eidosxr/spec/" --output-model-type pydantic_v2.BaseModel --base-class=eidosxr.spec._basemodel.EidosModel --use-subclass-enum --use-schema-description --use-field-description --use-one-literal-as-default

python "$ROOTDIR/autogen/gen_init.py"

# Fix circular import: world.py imports panel, but panel.py imports world (via node/__init__.py).
# Remove the panel import from world.py and defer all model_rebuild() calls that transitively
# reference panel.EidosPanel (World, Grid, Menu) to panel.py, where panel is fully defined.
WORLD_PY=$ROOTDIR/eidosxr/spec/node/world.py
GRID_PY=$ROOTDIR/eidosxr/spec/node/grid.py
MENU_PY=$ROOTDIR/eidosxr/spec/node/menu.py
PANEL_PY=$ROOTDIR/eidosxr/spec/panel.py

# Remove `panel` from world.py's import and its model_rebuild() call.
# datamodel-codegen emits either `from .. import common, panel` or a separate
# (possibly aliased) `from .. import panel as panel_1` line — strip both forms.
perl -p -i -e "s|from \.\. import common, panel|from .. import common|g" "$WORLD_PY"
perl -n -i -e "print unless /^from \.\. import panel( as panel_\d+)?\s*$/" "$WORLD_PY"
perl -p -i -e "s|^World\.model_rebuild\(\)$|# model_rebuild() called in panel.py after EidosPanel is defined to break circular import|g" "$WORLD_PY"

# Nested subclasses World, so its rebuild also resolves the panel annotation —
# defer it to panel.py with the others.
perl -p -i -e "s|^Nested\.model_rebuild\(\)$|# model_rebuild() called in panel.py after EidosPanel is defined to break circular import|g" "$WORLD_PY"

# Defer Grid.model_rebuild() - Grid references World which references panel.EidosPanel
perl -p -i -e "s|^Grid\.model_rebuild\(\)$|# model_rebuild() called in panel.py after EidosPanel is defined to break circular import|g" "$GRID_PY"

# Defer Menu.model_rebuild() - Menu references World which references panel.EidosPanel
perl -p -i -e "s|^Menu\.model_rebuild\(\)$|# model_rebuild() called in panel.py after EidosPanel is defined to break circular import|g" "$MENU_PY"

# In panel.py, rebuild deferred models with panel in the types namespace.
# Include the panel_1 alias so annotations from the aliased import form
# (`from .. import panel as panel_1`) also resolve.
perl -p -i -e "s|^EidosPanel\.model_rebuild\(\)$|import sys as _sys\n_panel_ns = {\"panel\": _sys.modules[__name__], \"panel_1\": _sys.modules[__name__]}\nworld.World.model_rebuild(_types_namespace=_panel_ns)\nworld.Nested.model_rebuild(_types_namespace=_panel_ns)\ngrid.Grid.model_rebuild(_types_namespace=_panel_ns)\nmenu.Menu.model_rebuild(_types_namespace=_panel_ns)\nEidosPanel.model_rebuild()|g" "$PANEL_PY"

#vegaspec is a special case - copy Altair wrapper to vegaspec.py
cp "$ROOTDIR/autogen/_vegaspec.py" "$ROOTDIR/eidosxr/spec/vegaspec.py"
