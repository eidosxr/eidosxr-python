import os

ROOTDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "eidosxr")
SPECDIR = os.path.join(ROOTDIR, "spec")


def write_init(curdir):
    with open(os.path.join(curdir, "__init__.py"), "w") as f:
        for name in sorted(os.listdir(curdir)):
            if (
                not name.startswith("_")
                and not name.startswith(".")
                and not name.endswith(".md")
            ):
                f.write(f"from .{name.replace('.py','')} import *\n")


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
    write_init(SPECDIR)
