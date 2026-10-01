# Hand-maintained — autogen/gen_init.py only rewrites the eidosxr/spec tree.
# Order is deliberate: spec (schema models) first, api (platform client)
# second, so api names win a collision (e.g. Dataset -> api.apimodels.Dataset).
from typing import TYPE_CHECKING as _TYPE_CHECKING

from .spec import *
from .api import *
from . import version

# Names that need the data extra (eidosxr[data]) — OceanQL, Query, altair and
# oceanql — resolve on first access (PEP 562), so `import eidosxr` stays light.
from ._optional import lazy_exports as _lazy_exports

__getattr__, __dir__ = _lazy_exports(__name__)

# `from eidosxr import *` binds what it did before the data stack became
# optional: every public name, plus the data names when the extra is installed.
__all__ = [_name for _name in __dir__() if not _name.startswith("_")]

if _TYPE_CHECKING:
    import altair
    from oceanum.datamesh import Query
    from .spec import oceanql
    from .spec.oceanql import OceanQL
