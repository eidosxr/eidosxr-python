ChangeLog
=========

0.12.4
------

Responsive layout (EID-194, EID-195). Regenerated from the EIDOS v0.12 schemas.

* ``Grid`` accepts ``responsive``: a list of ``ResponsiveItem`` (``maxWidth``,
  and optional ``gridSize`` and ``gridLayout``) giving the grid other layouts
  at narrower widths.
* ``Grid.gridLayout`` (and ``ResponsiveItem.gridLayout``) stay plain lists of
  ``GridLayoutItem``. The schema now shares ``gridLayout`` through ``$defs``,
  which the generator turns into a ``GridLayout`` root model; ``gen_models.sh``
  keeps the fields typed as lists so existing code that indexes or appends to
  them keeps working.
* ``Menu.position`` (top, left, bottom, right) is now honoured by the renderer
  and no longer defaults to ``'top'``: unset still means top, and specs no
  longer carry the field unless you set it.
* ``World`` (and nested worlds) accept ``maxPixelRatio``, the upper limit on the
  map canvas resolution. It is unset by default (the renderer then uses 2), so
  specs only carry it when you set it.

0.12.3
------

Spec templates (EID-190). Regenerated from the EIDOS v0.12 schemas, which add
two top-level fields to the specification.

* ``Eidos`` accepts ``parameters``: a list of ``TemplateParameter`` (``key``,
  ``label``, ``kind``, ``targets``, and optional ``required``, ``default`` and
  ``dependsOn``) that a spec template exposes for the user to fill in.
  ``ParameterKind`` is its ``kind`` enum.
* ``Eidos`` keeps top-level ``x-`` keys (e.g. ``"x-meta": {...}``) as given and
  writes them back out on ``model_dump``, ``spec()``, ``diff()``/``patch()`` and
  JSON output. Other unknown top-level keys are still rejected. The generated
  ``EidosSpecification`` model still forbids every extra key: the generator
  cannot express the schema's ``^x-`` pattern, so ``Eidos`` implements it.
* ``Eidos.model_dump_json()`` and ``str(spec)`` now omit null (unset) fields,
  consistent with ``model_dump()``. They previously wrote them out, e.g.
  ``"theme": null``, which the schema rejects.
* ``EidosConnection.create_template`` documents ``node_type="spec"`` for
  whole-specification templates, and accepts an ``Eidos`` as ``spec_json``.

0.12.2
------

* Regenerated from the EIDOS v0.12 schemas, which add ``"wave"`` to the gridded
  layer's particle mesh ``shape``.

0.12.1
------

Packaging change; the EIDOS schema (v0.12) and the public names are unchanged.

* **Breaking for data-helper users:** the data stack (oceanum, pandas,
  geopandas, xarray, altair, numpy) moved from the required dependencies to the
  ``data`` extra. ``pip install eidosxr`` now installs only pydantic, requests,
  jsonpatch and jinja2: the spec models, ``Eidos`` and the platform API client.
  If you use ``EidosDatasource``, ``EidosChart``, ``isotime``, ``OceanQL`` or
  the zarr consistency checks, install ``eidosxr[data]`` (or ``eidosxr[all]``).
* Importing ``eidosxr`` no longer loads the data stack. The data helpers import
  it when called and, without the extra, raise an ``ImportError`` naming
  ``pip install 'eidosxr[data]'``.
* ``from eidosxr import X`` and ``from eidosxr import *`` keep working for
  every name exported by 0.12.0. ``OceanQL``, ``Query``, ``altair`` and
  ``oceanql`` now resolve on first access. Without the data extra they are left
  out of ``dir()`` and ``from eidosxr import *``, and accessing them (including
  ``hasattr``) raises the ``ImportError``. ``from eidosxr.spec import *`` no
  longer binds them; import them by name.

0.1.0 (2024-02-13)
------------------

* Initial release.

