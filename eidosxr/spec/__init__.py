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
from .._optional import DATA_EXPORTS as _DATA_EXPORTS, data_export as _data_export


def __getattr__(name):
    return _data_export(name, __name__)


def __dir__():
    return sorted(set(globals()) | set(_DATA_EXPORTS))
