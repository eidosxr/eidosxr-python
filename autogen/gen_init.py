import os

ROOTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "eidosxr")
SPECDIR = os.path.join(ROOTDIR, "spec")

# Spec modules that need the optional data extra (eidosxr[data]). They are not
# star-imported by eidosxr/spec/__init__.py, so `import eidosxr.spec` stays
# light; their public names resolve lazily via eidosxr._optional.DATA_EXPORTS.
DATA_MODULES = {"oceanql.py"}

LAZY_FOOTER = '''

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
'''


def write_init(curdir, skip=(), footer=""):
    with open(os.path.join(curdir, "__init__.py"), "w") as f:
        for name in sorted(os.listdir(curdir)):
            if (
                not name.startswith("_")
                and not name.startswith(".")
                and not name.endswith(".md")
                and name not in skip
            ):
                f.write(f"from .{name.replace('.py','')} import *\n")
        f.write(footer)


def walk(curdir):
    for name in sorted(os.listdir(curdir)):
        if name.startswith("_") or name.startswith("."):
            continue
        if os.path.isdir(os.path.join(curdir, name)):
            write_init(os.path.join(curdir, name))
            walk(os.path.join(curdir, name))


if __name__ == "__main__":
    # Only the generated spec tree gets machine-written __init__ files.
    # eidosxr/__init__.py and eidosxr/api/__init__.py are hand-maintained —
    # regeneration must not rewrite them (import order there is deliberate).
    walk(SPECDIR)
    write_init(SPECDIR, skip=DATA_MODULES, footer=LAZY_FOOTER)
