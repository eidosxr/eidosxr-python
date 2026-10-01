"""Optional dependencies: the data stack behind the ``eidosxr[data]`` extra.

The core install (``pip install eidosxr``) covers the spec models and the
platform API client. The data helpers — :class:`eidosxr.EidosDatasource`,
:class:`eidosxr.EidosChart`, :func:`eidosxr.isotime`, :class:`eidosxr.OceanQL`
and the zarr coordinate checks — need oceanum, pandas, geopandas, xarray,
altair or numpy, which ship in the ``data`` extra. Those libraries are imported
only when a helper that needs them is used, through :func:`import_optional`.
"""

from __future__ import annotations

import importlib
from types import ModuleType
from typing import Any, Dict, Optional, Tuple

INSTALL_HINT = "pip install 'eidosxr[data]'"

#: Names exported by ``eidosxr`` and ``eidosxr.spec`` that need the data extra.
#: They are resolved on first access by the packages' PEP 562 ``__getattr__``,
#: so ``import eidosxr`` stays light. Maps name -> (module, attribute), where an
#: attribute of ``None`` means the module itself.
DATA_EXPORTS: Dict[str, Tuple[str, Optional[str]]] = {
    "OceanQL": ("eidosxr.spec.oceanql", "OceanQL"),
    "oceanql": ("eidosxr.spec.oceanql", None),
    # Re-exported by accident before 0.12.1 (star imports of oceanql.py and
    # vegaspec.py); kept so existing ``from eidosxr import ...`` lines work.
    "Query": ("oceanum.datamesh", "Query"),
    "altair": ("altair", None),
}


def import_optional(name: str) -> ModuleType:
    """Import a module from the data extra, or raise an ImportError naming it."""
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise ImportError(
            f"{name} is required for this feature but could not be imported "
            f"({exc}). Install the data extra: {INSTALL_HINT}"
        ) from exc


def data_export(name: str, module: str) -> Any:
    """Resolve a :data:`DATA_EXPORTS` name for a package's ``__getattr__``."""
    try:
        source, attr = DATA_EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {module!r} has no attribute {name!r}") from None
    # eidosxr's own data modules raise the install hint themselves.
    if source.startswith("eidosxr."):
        mod = importlib.import_module(source)
    else:
        mod = import_optional(source)
    return mod if attr is None else getattr(mod, attr)
