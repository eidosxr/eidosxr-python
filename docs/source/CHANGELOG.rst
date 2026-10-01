ChangeLog
=========

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
* ``from eidosxr import X`` keeps working for every name exported by 0.12.0;
  ``OceanQL``, ``Query``, ``altair`` and ``oceanql`` now resolve on first
  access.

0.1.0 (2024-02-13)
------------------

* Initial release.

