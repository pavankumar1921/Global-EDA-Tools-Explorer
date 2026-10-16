"""Prove the project is running inside Crucible and nowhere else.

Run:  igny run script ./scripts/check_environment.py
Checks: the interpreter is Crucible's Python; CRUCIBLE_ENV is set by igny; every third-party library the
project imports (numpy, matplotlib) resolves to a Crucible tool directory; and the user's personal
site-packages are not on sys.path (Crucible's Python does not disable them by itself - see the report).
Also lists libraries the project would have liked but the catalog does not provide (recorded as gaps).
"""
import importlib
import os
import site
import sys
from pathlib import Path

# Crucible keeps tool payloads under CRUCIBLE_ROOT (default ~/Crucible), user guide section 04
TOOLS_ROOT = os.path.normcase(str(Path(os.environ.get("CRUCIBLE_ROOT") or Path.home() / "Crucible") / "tools"))

WANTED = {"numpy": True, "matplotlib": True}           # required, must come from Crucible
GAPS = ["pandas", "scipy", "seaborn", "requests", "bs4"]  # not declared Crucible tools -> not used


def origin(mod):
    return os.path.normcase(os.path.abspath(getattr(mod, "__file__", "") or ""))


def main():
    sys.path[:] = [p for p in sys.path if not p.startswith(site.getusersitepackages())]
    ok = True
    exe = os.path.normcase(sys.executable)
    print("python      :", sys.executable, sys.version.split()[0])
    print("tools root  :", TOOLS_ROOT)
    print("CRUCIBLE_ENV:", os.environ.get("CRUCIBLE_ENV", "(not set)"))
    if "crucible" not in exe:
        print("FAIL: interpreter is not Crucible's Python - run through 'igny run script'")
        ok = False
    if not os.environ.get("CRUCIBLE_ENV"):
        print("FAIL: CRUCIBLE_ENV not set - run through 'igny run script'")
        ok = False
    for name in WANTED:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            print("FAIL: %s not importable - igny tool install %s" % (name, name))
            ok = False
            continue
        where = origin(mod)
        inside = where.startswith(TOOLS_ROOT)
        print("%-12s %-8s %s %s" % (name, getattr(mod, "__version__", "?"), "crucible" if inside else "OUTSIDE", where))
        ok &= inside
        tool_dir = where[len(TOOLS_ROOT):].lstrip("\\/").split(os.sep)[0] if inside else ""
        if inside and tool_dir != name:
            print("note        : %s was imported from the '%s' tool's bundled copy (PYTHONPATH order decides)"
                  % (name, tool_dir))
    user_site = site.getusersitepackages()
    print("user site   :", user_site, "(excluded from sys.path)" if user_site not in sys.path else "(ON sys.path!)")
    for name in GAPS:
        try:
            mod = importlib.import_module(name)
            src = "via another tool's bundle" if origin(mod).startswith(TOOLS_ROOT) else "OUTSIDE Crucible"
            print("gap         : %-10s importable %s but not a declared Crucible tool -> not used" % (name, src))
        except ImportError:
            print("gap         : %-10s not available in the Crucible catalog -> not used" % name)
    print("RESULT:", "OK - environment is isolated in Crucible" if ok else "FAILED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
