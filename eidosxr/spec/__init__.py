from .base import *
from .common import *
from .data import *
from .exceptions import *
from .features import *
from .geojson import *
from .node import *
from .panel import *
from .root import *
from .state import *
from .theme import *
from .vegaspec import *


# Names that need the data extra (eidosxr[data]) resolve on first access
# (PEP 562), so importing eidosxr.spec does not load the data stack.
from typing import TYPE_CHECKING as _TYPE_CHECKING

from .._optional import lazy_exports as _lazy_exports

__getattr__, __dir__ = _lazy_exports(__name__)

if _TYPE_CHECKING:
    import altair
    from oceanum.datamesh import Query
    from . import oceanql
    from .oceanql import OceanQL
