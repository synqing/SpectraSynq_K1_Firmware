"""PlatformIO pre-build hook: inject compile-time build-provenance defines.

Lane N5 (release engineering). Until now a running K1 unit could not be tied
back to the exact source it was built from: ``FIRMWARE_VERSION`` is a coarse
integer shared across many commits (the device-build-registry notes 40103 does
NOT discriminate lineages), and there were no git tags. This script stamps three
defines into every translation unit so the firmware can report its own build
identity over serial (see the ``build`` command in serial/serial_menu.h):

    -DK1_BUILD_GIT_HASH="<short hash>"   git rev-parse --short HEAD (or "unknown")
    -DK1_BUILD_EPOCH=<unix seconds>      wall-clock build time
    -DK1_BUILD_ENV="<$PIOENV>"           the PlatformIO environment name

Registered under env:k1_hardware extra_scripts, so every derived env (all of
which ``extends = env:k1_hardware``) inherits the stamp automatically.

DISCIPLINE: this hook MUST NEVER fail a build. If git is unavailable, not on
PATH, or the tree is not a repository, the hash degrades to "unknown" rather
than raising. Provenance is metadata, not a gate.

The string defines use the ``\\"value\\"`` CPPDEFINES idiom (PlatformIO's
documented pattern) so the quotes survive onto the compiler command line as
genuine C string literals.
"""
from __future__ import annotations

import os
import subprocess
import time

Import("env")  # noqa: F821  (injected by PlatformIO/SCons)


def _git_short_hash() -> str:
    """Return the short HEAD hash, or "unknown" if git is unavailable.

    Never raises: a missing git binary, a non-repo tree, or any subprocess
    failure all degrade to "unknown" so the build proceeds.
    """
    project_dir = env.subst("$PROJECT_DIR")  # noqa: F821
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=project_dir,
            stderr=subprocess.DEVNULL,
        )
        value = out.strip().decode("utf-8", "replace")
        return value or "unknown"
    except Exception:
        return "unknown"


def _release_tag(prefix: str) -> str:
    """Return the release tag on HEAD that starts with ``prefix``.

    "untagged" when HEAD carries no such tag, "dirty" appended when tracked
    firmware sources differ from HEAD. Never raises.
    """
    project_dir = env.subst("$PROJECT_DIR")  # noqa: F821
    try:
        out = subprocess.check_output(
            ["git", "tag", "--points-at", "HEAD", "--list", prefix + "*"],
            cwd=project_dir,
            stderr=subprocess.DEVNULL,
        )
        tags = sorted(t for t in out.decode("utf-8", "replace").split() if t)
        tag = tags[-1] if tags else "untagged"
        dirty = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--",
             "SPECTRASYNQ_K1_FIRMWARE", "platformio.ini"],
            cwd=project_dir,
            stderr=subprocess.DEVNULL,
        ).returncode
        return tag + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


_GIT_HASH = _git_short_hash()
_EPOCH = int(time.time())
_PIOENV = env.subst("$PIOENV") or "unknown"  # noqa: F821

_DEFINES = [
    ("K1_BUILD_GIT_HASH", '\\"%s\\"' % _GIT_HASH),
    ("K1_BUILD_EPOCH", str(_EPOCH)),
    ("K1_BUILD_ENV", '\\"%s\\"' % _PIOENV),
]
# Release envs only (e.g. k1_fe: custom_release_tag_prefix = fe-). Other envs
# get no K1_BUILD_TAG, so their command lines and binaries are unchanged.
_TAG_PREFIX = env.GetProjectOption("custom_release_tag_prefix", "")  # noqa: F821
_TAG = _release_tag(_TAG_PREFIX) if _TAG_PREFIX else None
if _TAG is not None:
    _DEFINES.append(("K1_BUILD_TAG", '\\"%s\\"' % _TAG))

env.Append(CPPDEFINES=_DEFINES)  # noqa: F821

print(
    "[k1-build-provenance] env=%s git=%s epoch=%d%s"
    % (_PIOENV, _GIT_HASH, _EPOCH, (" tag=%s" % _TAG) if _TAG is not None else "")
)
