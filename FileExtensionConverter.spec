# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for File Extension Converter.

The engine imports optional libraries lazily via importlib (tools.require_module),
so PyInstaller's static analysis cannot see them. We list them as hidden imports
and only include the optional ones that are actually installed in this env.
"""
from PyInstaller.utils.hooks import collect_submodules

# always-bundled (declared in requirements core)
hidden = ["PIL", "PIL.Image", "yaml", "xmltodict", "toml", "openpyxl"]
hidden += collect_submodules("markdown")  # markdown loads extensions dynamically

# optional engines: bundle only if present so the build never fails on a missing one
_optional = [
    "fitz", "fontTools", "fontTools.ttLib", "trimesh", "py7zr", "rarfile",
    "cairosvg", "rawpy", "imageio", "imageio.v2", "imageio.v3",
    "pillow_heif", "brotli",
]
for _m in _optional:
    try:
        __import__(_m.split(".")[0])
        hidden.append(_m)
    except Exception:
        pass

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy.testing"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="File Extension Converter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="File Extension Converter",
)
