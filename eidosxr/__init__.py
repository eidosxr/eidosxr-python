# Hand-maintained — autogen/gen_init.py only rewrites the eidosxr/spec tree.
# Order is deliberate: spec (schema models) first, api (platform client)
# second, so api names win a collision (e.g. Dataset -> api.apimodels.Dataset).
from .spec import *
from .api import *
from . import version
