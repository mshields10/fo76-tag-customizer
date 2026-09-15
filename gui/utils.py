"""Utility helpers shared across the GUI.

  get_resource_path       — resolves bundled asset paths in both dev and PyInstaller
  get_appdata_path        — writable user-data directory under %APPDATA%
  companion_strings_path  — swap extension on a .STRINGS path (→ .DLSTRINGS / .ILSTRINGS)
  detect_fo76_data_dir    — finds the FO76 Data folder at common Steam locations
  populate_default_settings — fills QSettings with smart defaults on first run
"""
import os
import sys

from PySide6.QtCore import QSettings


# ---------------------------------------------------------------------------
# PyInstaller-aware resource path
# ---------------------------------------------------------------------------

def get_resource_path(relative_path: str) -> str:
    """Return the absolute path to a bundled asset.

    When running as a PyInstaller .exe, assets are unpacked to sys._MEIPASS
    at launch.  In development they live relative to the project root.
    """
    if hasattr(sys, '_MEIPASS'):
        # Bundled: PyInstaller unpacks data files here
        return os.path.join(sys._MEIPASS, relative_path)
    # Development: gui/ is one level below the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(project_root, relative_path)


# ---------------------------------------------------------------------------
# User-data directory
# ---------------------------------------------------------------------------

def get_appdata_path(filename: str = "") -> str:
    """Return a path under %APPDATA%\\FO76TagCustomizer\\, creating it if needed."""
    base = os.path.join(
        os.environ.get("APPDATA", os.path.expanduser("~")),
        "FO76TagCustomizer"
    )
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, filename) if filename else base


# ---------------------------------------------------------------------------
# Companion string-file path helper
# ---------------------------------------------------------------------------

def companion_strings_path(strings_path: str, new_ext: str) -> str:
    """Return a sibling path with a different extension.

    companion_strings_path("Data/strings/SeventySix_en.STRINGS", ".DLSTRINGS")
    → "Data/strings/SeventySix_en.DLSTRINGS"

    Used to derive .DLSTRINGS / .ILSTRINGS output paths from the configured
    .STRINGS output path without requiring separate user-facing settings fields.
    """
    base = os.path.splitext(strings_path)[0]
    return base + new_ext


# ---------------------------------------------------------------------------
# FO76 installation detection
# ---------------------------------------------------------------------------

# Steam library roots to probe.  The user may have FO76 on any drive.
_STEAM_ROOTS = [
    r"C:\Program Files (x86)\Steam",
    r"C:\Program Files\Steam",
    r"D:\Steam",
    r"D:\SteamLibrary",
    r"E:\Steam",
    r"E:\SteamLibrary",
    r"F:\Steam",
    r"F:\SteamLibrary",
]
_FO76_REL = r"steamapps\common\Fallout76\Data"


def detect_fo76_data_dir() -> str:
    """Return the FO76 Data directory path if found at a known Steam location.

    Returns an empty string if nothing is found — callers should treat this
    as 'auto-detect failed, ask the user'.
    """
    for root in _STEAM_ROOTS:
        candidate = os.path.join(root, _FO76_REL)
        if os.path.isdir(candidate):
            return candidate
    return ""


# ---------------------------------------------------------------------------
# First-run default settings
# ---------------------------------------------------------------------------

def populate_default_settings():
    """Set sensible defaults in QSettings for any path not yet configured.

    Safe to call on every launch — existing values are never overwritten.
    The rules JSON is always resolved to the bundled asset so the user
    never has to find or manage it manually.
    """
    s = QSettings()

    def _default(key: str, value: str):
        """Set key only if it has no value yet."""
        if not s.value(key, ""):
            s.setValue(key, value)

    # The rules JSON is bundled with the app — set it silently every launch
    # so it stays current even after an app update.
    s.setValue("paths/rules_json", get_resource_path("data/tidy_wasteland_analysis.json"))

    # User-writable files default to a dedicated AppData folder so nothing
    # ends up in Program Files or the game's Data directory by accident.
    _default("paths/vanilla_strings",   get_appdata_path("seventysix_en.strings"))
    _default("paths/vanilla_dlstrings", get_appdata_path("seventysix_en.dlstrings"))
    _default("paths/vanilla_ilstrings", get_appdata_path("seventysix_en.ilstrings"))
    _default("paths/custom_rules",      get_appdata_path("custom_rules.json"))

    # Try to auto-detect FO76 for the BA2 and compiled-output paths.
    fo76_data = detect_fo76_data_dir()
    if fo76_data:
        _default("paths/ba2",
                 os.path.join(fo76_data, "SeventySix - Localization.ba2"))
        _default("paths/compiled_output",
                 os.path.join(fo76_data, r"strings\SeventySix_en.STRINGS"))
