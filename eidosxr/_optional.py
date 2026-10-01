"""Optional dependencies: the data stack behind the ``eidosxr[data]`` extra.

The core install (``pip install eidosxr``) covers the spec models and the
platform API client. The data helpers — :class:`eidosxr.EidosDatasource`,
:class:`eidosxr.EidosChart`, :func:`eidosxr.isotime`, :class:`eidosxr.OceanQL`
and the zarr consistency checks — need oceanum, pandas, geopandas, xarray,
altair or numpy, which ship in the ``data`` extra. Those libraries are imported
only when a helper that needs them is used, through :func:`import_optional`.
"""

from __future__ import annotations

import functools
import importlib
import importlib.util
import sys
from types import ModuleType
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

INSTALL_HINT = "pip install 'eidosxr[data]'"


class DataExport(NamedTuple):
    module: str  #: the module holding the name
    attr: Optional[str]  #: the attribute, or None for the module itself
    requires: str  #: the top-level data-extra package it needs


#: Names exported by ``eidosxr`` and ``eidosxr.spec`` that need the data extra.
#: They resolve on first access through :func:`lazy_exports`, so
#: ``import eidosxr`` stays light.
DATA_EXPORTS: Dict[str, DataExport] = {
    "OceanQL": DataExport("eidosxr.spec.oceanql", "OceanQL", "oceanum"),
    "oceanql": DataExport("eidosxr.spec.oceanql", None, "oceanum"),
    # Re-exported by accident before 0.12.1 (star imports of oceanql.py and
    # vegaspec.py); kept so existing ``from eidosxr import ...`` lines work.
    "Query": DataExport("oceanum.datamesh", "Query", "oceanum"),
    "altair": DataExport("altair", None, "altair"),
}


@functools.lru_cache(maxsize=None)
def import_optional(name: str) -> ModuleType:
    """Import a module from the data extra.

    If the module (or its package) is not installed, raise an ImportError that
    names the extra. Any other ImportError — a broken installed package — is
    re-raised unchanged. Successful imports are cached; failures are not.
    """
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        if exc.name and (name == exc.name or name.startswith(exc.name + ".")):
            raise ImportError(
                f"{name} is required for this feature but is not installed. "
                f"Install the data extra: {INSTALL_HINT}",
                name=exc.name,
            ) from exc
        raise


def is_installed(package: str) -> bool:
    """Whether a top-level package can be imported, without importing it."""
    try:
        return importlib.util.find_spec(package) is not None
    except (ImportError, ValueError):
        return False


def _resolve(name: str) -> Any:
    export = DATA_EXPORTS[name]
    # eidosxr's own data modules raise the install hint themselves.
    if export.module.startswith("eidosxr."):
        module = importlib.import_module(export.module)
    else:
        module = import_optional(export.module)
    return module if export.attr is None else getattr(module, export.attr)


def lazy_exports(
    module_name: str,
) -> Tuple[Callable[[str], Any], Callable[[], List[str]]]:
    """PEP 562 ``__getattr__`` and ``__dir__`` for a package's data exports.

    ``__getattr__`` resolves a :data:`DATA_EXPORTS` name on first access and
    caches it in the package; without the data extra it raises an ImportError
    naming it. ``__dir__`` lists the data names only when the package they need
    is installed, so introspection (``help()``, ``inspect.getmembers``) of a
    core install does not trip over them.
    """
    namespace = sys.modules[module_name].__dict__

    def __getattr__(name: str) -> Any:
        if name not in DATA_EXPORTS:
            raise AttributeError(f"module {module_name!r} has no attribute {name!r}")
        value = _resolve(name)
        namespace[name] = value
        return value

    def __dir__() -> List[str]:
        available = {n for n, e in DATA_EXPORTS.items() if is_installed(e.requires)}
        return sorted(set(namespace) | available)

    return __getattr__, __dir__
