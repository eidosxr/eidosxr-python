# Hand-maintained — autogen/gen_init.py only rewrites the eidosxr/spec tree.
# Order is deliberate: spec (schema models) first, api (platform client)
# second, so api names win a collision (e.g. Dataset -> api.apimodels.Dataset).
from .spec import *
from .api import *
from . import version

# Names that need the data extra (eidosxr[data]) — OceanQL and friends —
# resolve on first access (PEP 562), so `import eidosxr` stays light.
from ._optional import DATA_EXPORTS as _DATA_EXPORTS, data_export as _data_export


def __getattr__(name):
    return _data_export(name, __name__)


def __dir__():
    return sorted(set(globals()) | set(_DATA_EXPORTS))
