# -*- coding: utf-8 -*-
"""Conversion engine.

Every (source, target) pair listed in ``conversions_data.PAIRS`` is registered
and routed to a concrete handler.  Handlers use the best available backend:
Pillow / ffmpeg / LibreOffice / fonttools / trimesh / pure-Python, etc.
When a required engine is absent a :class:`tools.ToolMissing` is raised with a
localized, actionable message.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

from .conversions_data import PAIRS, CATEGORIES
from . import tools
from .tools import ToolMissing


# --------------------------------------------------------------------------- #
#  Pair registry & routing
# --------------------------------------------------------------------------- #

def _u(ext: str) -> str:
    return ext.strip().lstrip(".").upper()


# (SRC, DST) -> category, honoring 双方向 (bidirectional) by adding the reverse.
PAIR_CATEGORY: dict[tuple[str, str], str] = {}
PAIR_DIRECTION: dict[tuple[str, str], str] = {}
for _cat, _s, _d, _dir in PAIRS:
    su, du = _u(_s), _u(_d)
    PAIR_CATEGORY[(su, du)] = _cat
    PAIR_DIRECTION[(su, du)] = _dir
    if _dir.startswith("双方向"):
        PAIR_CATEGORY.setdefault((du, su), _cat)
        PAIR_DIRECTION.setdefault((du, su), _dir)

VIDEO_FMTS = {"MP4", "MKV", "AVI", "MOV", "WMV", "FLV", "WEBM", "MPEG",
              "3GP", "TS", "M2TS", "VOB", "OGV", "M4V"}
AUDIO_FMTS = {"MP3", "WAV", "AAC", "FLAC", "M4A", "OGG", "WMA", "OPUS",
              "AIFF", "AMR", "APE", "WV", "MID"}
ANIM_TARGETS = {"GIF", "APNG", "WEBP"}


def category_for(src: str, dst: str) -> str | None:
    """Return the category that supports src->dst, or None if unsupported.
    Handles the special '動画全般' (any video) source rows."""
    src, dst = _u(src), _u(dst)
    if (src, dst) in PAIR_CATEGORY:
        return PAIR_CATEGORY[(src, dst)]
    # '動画全般' rows: any video file -> the listed target
    if src in VIDEO_FMTS and ("動画全般", dst) in PAIR_CATEGORY:
        return PAIR_CATEGORY[("動画全般", dst)]
    return None


def is_supported(src: str, dst: str) -> bool:
    return category_for(src, dst) is not None


# --------------------------------------------------------------------------- #
#  Subprocess helper
# --------------------------------------------------------------------------- #

def _run(cmd: list[str], cwd: str | None = None, timeout: int = 1800) -> None:
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError as e:
        raise ToolMissing(f"実行ファイルが見つかりません: {cmd[0]}") from e
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or b"").decode("utf-8", "replace")
        tail = "\n".join(err.strip().splitlines()[-15:])
        raise RuntimeError(f"変換コマンドが失敗しました (code {proc.returncode}):\n{tail}")


# --------------------------------------------------------------------------- #
#  IMAGE
# --------------------------------------------------------------------------- #

_VECTOR_IN = {"SVG", "EPS", "AI", "PDF"}


def _load_pillow_image(infile: str, src: str):
    """Decode ``infile`` (whose logical format is ``src``) into a Pillow Image."""
    Image = tools.require_module("PIL.Image", "Pillow")

    if src == "HEIC":
        if tools.have_module("pillow_heif"):
            import pillow_heif
            pillow_heif.register_heif_opener()
        else:
            raise ToolMissing("HEIC の読み込みには pillow-heif が必要です。\n"
                              "インストール: pip install pillow-heif")
        return Image.open(infile)

    if src == "RAW" or src in {"CR2", "NEF", "ARW", "DNG", "RW2", "ORF"}:
        rawpy = tools.require_module("rawpy")
        import numpy as np  # noqa
        with rawpy.imread(infile) as raw:
            rgb = raw.postprocess()
        return Image.fromarray(rgb)

    if src == "SVG":
        cairosvg = tools.require_module("cairosvg")
        png_bytes = cairosvg.svg2png(url=infile)
        import io
        return Image.open(io.BytesIO(png_bytes))

    if src in {"EXR", "HDR"}:
        iio = tools.require_module("imageio.v3", "imageio")
        import numpy as np
        arr = iio.imread(infile)
        if arr.dtype != "uint8":
            import numpy as _np
            arr = (_np.clip(arr, 0, 1) * 255).astype("uint8") if arr.max() <= 1 \
                else (arr / arr.max() * 255).astype("uint8")
        return Image.fromarray(arr)

    if src in {"EPS", "AI"}:
        # Pillow reads EPS via Ghostscript; AI files are usually EPS/PDF compatible.
        if not tools.ghostscript():
            raise ToolMissing(
                "EPS/AI のラスタライズには Ghostscript が必要です。\n"
                "インストール: https://ghostscript.com/releases/gsdnld.html")
        img = Image.open(infile)
        img.load(scale=2)
        return img

    # default: let Pillow figure it out (PSD, JPEG, PNG, BMP, GIF, TIFF, ICO,
    # WebP, TGA, PPM/PGM/PBM, XBM, XPM, ...)
    return Image.open(infile)


def convert_image(infile: str, outfile: str, src: str, dst: str) -> str:
    Image = tools.require_module("PIL.Image", "Pillow")

    # vector -> vector / pdf, handled before rasterizing
    if src == "SVG" and dst in {"PDF", "EPS"}:
        cairosvg = tools.require_module("cairosvg")
        if dst == "PDF":
            cairosvg.svg2pdf(url=infile, write_to=outfile)
        else:
            cairosvg.svg2ps(url=infile, write_to=outfile)
        return outfile
    if src == "AI" and dst in {"PDF", "EPS", "SVG"}:
        if dst == "PDF" and tools.ghostscript():
            _run([tools.ghostscript(), "-dNOPAUSE", "-dBATCH", "-sDEVICE=pdfwrite",
                  f"-sOutputFile={outfile}", infile])
            return outfile
        if tools.inkscape():
            _run([tools.inkscape(), infile, f"--export-filename={outfile}"])
            return outfile
        raise ToolMissing("AI の変換には Inkscape か Ghostscript が必要です。")

    img = _load_pillow_image(infile, src)

    # ---- save with format-specific handling ----
    save_fmt = {"JPG": "JPEG", "JPEG": "JPEG", "TIF": "TIFF", "TIFF": "TIFF"}.get(dst, dst)

    if dst in {"JPEG", "BMP"}:
        if img.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            img = img.convert("RGBA")
            bg.paste(img, mask=img.split()[-1])
            img = bg
        elif img.mode != "RGB":
            img = img.convert("RGB")
        img.save(outfile, save_fmt)
        return outfile

    if dst == "ICO":
        img = img.convert("RGBA")
        img.save(outfile, "ICO",
                 sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        return outfile

    if dst == "PDF":
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(outfile, "PDF")
        return outfile

    if dst == "PBM":
        img.convert("1").save(outfile, "PPM")
        return outfile
    if dst == "PGM":
        img.convert("L").save(outfile, "PPM")
        return outfile
    if dst == "PPM":
        img.convert("RGB").save(outfile, "PPM")
        return outfile

    if dst in {"EXR", "HDR"}:
        iio = tools.require_module("imageio.v2", "imageio")
        import numpy as np
        iio.imwrite(outfile, np.asarray(img))
        return outfile

    if dst == "XPM":
        # Pillow cannot write XPM; use ImageMagick if available.
        if tools.imagemagick():
            _run([tools.imagemagick(), infile, outfile])
            return outfile
        raise ToolMissing("XPM の書き出しには ImageMagick が必要です。")

    # GIF / PNG / WEBP / TIFF / TGA / XBM ...
    if dst in {"PNG", "WEBP"} and img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
        img = img.convert("RGBA")
    if dst == "GIF":
        img = img.convert("P", palette=Image.ADAPTIVE) if img.mode != "P" else img
    try:
        img.save(outfile, save_fmt)
    except (KeyError, ValueError, OSError) as e:
        raise RuntimeError(f"{src}→{dst} の保存に失敗しました: {e}") from e
    return outfile


# --------------------------------------------------------------------------- #
#  AUDIO / VIDEO  (ffmpeg)
# --------------------------------------------------------------------------- #

def convert_av(infile: str, outfile: str, src: str, dst: str) -> str:
    ff = tools.require_exe(
        tools.ffmpeg, "FFmpeg",
        "https://www.gyan.dev/ffmpeg/builds/ から取得し PATH に追加 (または winget install ffmpeg)")

    base = [ff, "-y", "-i", infile]

    # video -> animated image
    if dst in ANIM_TARGETS and src in VIDEO_FMTS:
        vf = "fps=15,scale=480:-1:flags=lanczos"
        if dst == "GIF":
            cmd = base + ["-vf", vf, outfile]
        elif dst == "APNG":
            cmd = base + ["-vf", vf, "-f", "apng", "-plays", "0", outfile]
        else:  # animated WEBP
            cmd = base + ["-vf", vf, "-vcodec", "libwebp", "-loop", "0",
                          "-an", "-vsync", "0", outfile]
        _run(cmd)
        return outfile

    # video -> audio (extraction)
    if src in VIDEO_FMTS and dst in AUDIO_FMTS:
        _run(base + ["-vn", outfile])
        return outfile

    # MIDI needs a synthesizer/soundfont; ffmpeg alone usually cannot render it
    if src == "MID":
        try:
            _run(base + [outfile])
            return outfile
        except RuntimeError as e:
            raise ToolMissing(
                "MIDI の音声化には FluidSynth とサウンドフォント(.sf2)が必要です。\n"
                "例: winget install FluidSynth、その後 SoundFont を指定してください。") from e

    # generic audio/video transcode (ffmpeg picks codecs from the extension)
    _run(base + [outfile])
    return outfile


# --------------------------------------------------------------------------- #
#  DOCUMENT / TEXT
# --------------------------------------------------------------------------- #

_OFFICE = {"DOCX", "DOC", "ODT", "RTF", "XLSX", "XLS", "ODS",
           "PPTX", "PPT", "ODP", "HTML"}
_EBOOK = {"EPUB", "MOBI", "AZW3"}


def _soffice_convert(infile: str, outfile: str, target_filter: str) -> str:
    so = tools.require_exe(
        tools.soffice, "LibreOffice",
        "https://www.libreoffice.org/download/ からインストール")
    outdir = tempfile.mkdtemp(prefix="fec_so_")
    _run([so, "--headless", "--norestore", "--convert-to", target_filter,
          "--outdir", outdir, infile])
    produced = os.path.join(outdir, os.path.splitext(os.path.basename(infile))[0]
                            + "." + target_filter.split(":")[0])
    if not os.path.isfile(produced):
        cands = [os.path.join(outdir, f) for f in os.listdir(outdir)]
        if not cands:
            raise RuntimeError("LibreOffice が出力ファイルを生成しませんでした。")
        produced = cands[0]
    shutil.move(produced, outfile)
    shutil.rmtree(outdir, ignore_errors=True)
    return outfile


def convert_document(infile: str, outfile: str, src: str, dst: str) -> str:
    # ---- spreadsheet <-> csv/tsv : do natively (no LibreOffice needed) ----
    if {src, dst} & {"CSV", "TSV"} and {src, dst} & {"XLSX", "XLS", "ODS"}:
        return _spreadsheet_text(infile, outfile, src, dst)

    # ---- trivial text conversions ----
    if src == "TXT" and dst == "MD":
        shutil.copyfile(infile, outfile)
        return outfile
    if src == "MD" and dst == "TXT":
        shutil.copyfile(infile, outfile)
        return outfile
    if src == "TXT" and dst == "HTML":
        import html
        text = open(infile, encoding="utf-8", errors="replace").read()
        open(outfile, "w", encoding="utf-8").write(
            f"<!doctype html><meta charset='utf-8'><pre>{html.escape(text)}</pre>")
        return outfile
    if src == "MD" and dst == "HTML":
        md = tools.require_module("markdown")
        text = open(infile, encoding="utf-8", errors="replace").read()
        open(outfile, "w", encoding="utf-8").write(
            "<!doctype html><meta charset='utf-8'>\n" + md.markdown(text, extensions=["extra"]))
        return outfile

    # ---- PDF / PPTX -> image ----
    if dst in {"JPEG", "PNG", "TIFF"} and src in {"PDF", "PPTX"}:
        pdf = infile
        if src == "PPTX":
            tmp_pdf = os.path.join(tempfile.mkdtemp(prefix="fec_pdf_"), "tmp.pdf")
            _soffice_convert(infile, tmp_pdf, "pdf")
            pdf = tmp_pdf
        return _pdf_to_images(pdf, outfile, dst)

    # ---- ebooks (Calibre) ----
    if src in _EBOOK or dst in _EBOOK:
        cv = tools.require_exe(
            tools.calibre, "Calibre (ebook-convert)",
            "https://calibre-ebook.com/download からインストール")
        _run([cv, infile, outfile])
        return outfile

    # ---- everything else via LibreOffice ----
    # target filter: a few formats need an explicit LO filter name
    filt = {
        "PDF": "pdf", "DOCX": "docx", "DOC": "doc", "ODT": "odt", "RTF": "rtf",
        "HTML": "html", "TXT": "txt", "XLSX": "xlsx", "XLS": "xls", "ODS": "ods",
        "CSV": "csv", "PPTX": "pptx", "PPT": "ppt", "ODP": "odp", "MD": "txt",
    }.get(dst)
    if not filt:
        raise ToolMissing(f"{src}→{dst} は未対応のドキュメント変換です。")
    return _soffice_convert(infile, outfile, filt)


def _spreadsheet_text(infile, outfile, src, dst):
    import csv
    if src in {"XLSX", "XLS", "ODS"}:
        load = tools.require_module("openpyxl") if src == "XLSX" else None
        if src == "XLSX":
            wb = load.load_workbook(infile, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
        else:
            return _soffice_convert(infile, outfile, "csv" if dst == "CSV" else "csv")
        delim = "\t" if dst == "TSV" else ","
        with open(outfile, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f, delimiter=delim)
            for r in rows:
                w.writerow(["" if c is None else c for c in r])
        return outfile
    else:  # csv/tsv -> xlsx
        openpyxl = tools.require_module("openpyxl")
        delim = "\t" if src == "TSV" else ","
        wb = openpyxl.Workbook()
        ws = wb.active
        with open(infile, newline="", encoding="utf-8", errors="replace") as f:
            for row in csv.reader(f, delimiter=delim):
                ws.append(row)
        wb.save(outfile)
        return outfile


def _pdf_to_images(pdf, outfile, dst):
    fitz = tools.require_module("fitz", "PyMuPDF")
    doc = fitz.open(pdf)
    fmt = {"JPEG": "jpg", "PNG": "png", "TIFF": "png"}[dst]
    pages = []
    tmpd = tempfile.mkdtemp(prefix="fec_img_")
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        p = os.path.join(tmpd, f"page_{i+1:03d}.{fmt}")
        pix.save(p)
        pages.append(p)
    if dst == "TIFF":
        Image = tools.require_module("PIL.Image", "Pillow")
        imgs = [Image.open(p).convert("RGB") for p in pages]
        imgs[0].save(outfile, "TIFF", save_all=True, append_images=imgs[1:])
        return outfile
    if len(pages) == 1:
        shutil.move(pages[0], outfile)
        return outfile
    # multiple pages -> zip alongside requested name
    import zipfile
    zpath = os.path.splitext(outfile)[0] + "_pages.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in pages:
            z.write(p, os.path.basename(p))
    return zpath


# --------------------------------------------------------------------------- #
#  DATA / CODE  (pure python)
# --------------------------------------------------------------------------- #

def _data_load(path: str, fmt: str):
    import csv
    if fmt in {"CSV", "TSV"}:
        delim = "\t" if fmt == "TSV" else ","
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            return list(csv.DictReader(f, delimiter=delim))
    if fmt == "JSON":
        import json
        return json.load(open(path, encoding="utf-8"))
    if fmt == "YAML":
        yaml = tools.require_module("yaml", "PyYAML")
        return yaml.safe_load(open(path, encoding="utf-8"))
    if fmt == "TOML":
        try:
            import tomllib as t
            return t.load(open(path, "rb"))
        except ModuleNotFoundError:
            t = tools.require_module("toml")
            return t.load(open(path, encoding="utf-8"))
    if fmt == "XML":
        xmltodict = tools.require_module("xmltodict")
        return xmltodict.parse(open(path, "rb").read())
    if fmt == "INI":
        import configparser
        cp = configparser.ConfigParser()
        cp.read(path, encoding="utf-8")
        return {s: dict(cp.items(s)) for s in cp.sections()}
    raise ToolMissing(f"未対応のデータ形式: {fmt}")


def _data_dump(obj, path: str, fmt: str):
    import csv
    if fmt in {"CSV", "TSV"}:
        delim = "\t" if fmt == "TSV" else ","
        rows = obj if isinstance(obj, list) else [obj]
        rows = [r if isinstance(r, dict) else {"value": r} for r in rows]
        keys = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys, delimiter=delim)
            w.writeheader()
            for r in rows:
                w.writerow(r)
        return
    if fmt == "JSON":
        import json
        json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return
    if fmt == "YAML":
        yaml = tools.require_module("yaml", "PyYAML")
        yaml.safe_dump(obj, open(path, "w", encoding="utf-8"),
                       allow_unicode=True, sort_keys=False)
        return
    if fmt == "TOML":
        t = tools.require_module("toml")
        data = obj if isinstance(obj, dict) else {"items": obj}
        t.dump(data, open(path, "w", encoding="utf-8"))
        return
    if fmt == "XML":
        xmltodict = tools.require_module("xmltodict")
        if not (isinstance(obj, dict) and len(obj) == 1):
            obj = {"root": obj}
        open(path, "w", encoding="utf-8").write(xmltodict.unparse(obj, pretty=True))
        return
    if fmt == "INI":
        import configparser
        cp = configparser.ConfigParser()
        data = obj if isinstance(obj, dict) else {"items": obj}
        for sec, vals in data.items():
            if not isinstance(vals, dict):
                vals = {"value": vals}
            cp[str(sec)] = {str(k): str(v) for k, v in vals.items()}
        cp.write(open(path, "w", encoding="utf-8"))
        return
    raise ToolMissing(f"未対応のデータ形式: {fmt}")


def convert_data(infile: str, outfile: str, src: str, dst: str) -> str:
    obj = _data_load(infile, src)
    _data_dump(obj, outfile, dst)
    return outfile


# --------------------------------------------------------------------------- #
#  3D / CAD
# --------------------------------------------------------------------------- #

_TRIMESH_FMTS = {"OBJ", "STL", "PLY", "GLTF", "GLB", "DAE", "OFF", "3MF"}


def convert_3d(infile: str, outfile: str, src: str, dst: str) -> str:
    if src in _TRIMESH_FMTS and dst in _TRIMESH_FMTS:
        trimesh = tools.require_module("trimesh")
        scene = trimesh.load(infile, force="scene")
        scene.export(outfile)
        return outfile
    if src in {"FBX", "3DS"} or dst in {"FBX", "3DS"}:
        if tools.have_module("pyassimp"):
            import pyassimp
            with pyassimp.load(infile) as sc:
                pyassimp.export(sc, outfile, file_type=dst.lower())
            return outfile
        raise ToolMissing("FBX/3DS の変換には assimp (pyassimp) が必要です。\n"
                          "インストール: pip install pyassimp と Assimp 本体")
    if {src, dst} <= {"DWG", "DXF"}:
        if src == "DXF" and dst == "DWG":
            raise ToolMissing("DXF→DWG は ODA File Converter 等が必要です。")
        raise ToolMissing("DWG の読み込みには ODA File Converter 等が必要です。")
    if {src, dst} & {"STEP", "STP", "IGES", "IGS"}:
        raise ToolMissing("STEP/IGES (CAD) の変換には FreeCAD / OpenCASCADE が必要です。")
    raise ToolMissing(f"{src}→{dst} の 3D 変換は未対応です。")


# --------------------------------------------------------------------------- #
#  ARCHIVE
# --------------------------------------------------------------------------- #

def _extract_archive(path: str, fmt: str, dest: str) -> None:
    if fmt == "ZIP":
        import zipfile
        with zipfile.ZipFile(path) as z:
            z.extractall(dest)
    elif fmt in {"TAR", "GZ", "BZ2", "XZ"}:
        import tarfile
        with tarfile.open(path) as t:
            t.extractall(dest)
    elif fmt == "7Z":
        py7zr = tools.require_module("py7zr")
        with py7zr.SevenZipFile(path, "r") as z:
            z.extractall(dest)
    elif fmt == "RAR":
        rarfile = tools.require_module("rarfile")
        with rarfile.RarFile(path) as r:
            r.extractall(dest)
    else:
        raise ToolMissing(f"未対応のアーカイブ形式: {fmt}")


def _create_archive(srcdir: str, outfile: str, fmt: str) -> str:
    if fmt == "ZIP":
        import zipfile
        with zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED) as z:
            for root, _d, files in os.walk(srcdir):
                for fn in files:
                    fp = os.path.join(root, fn)
                    z.write(fp, os.path.relpath(fp, srcdir))
    elif fmt in {"TAR", "GZ", "BZ2", "XZ"}:
        import tarfile
        mode = {"TAR": "w", "GZ": "w:gz", "BZ2": "w:bz2", "XZ": "w:xz"}[fmt]
        with tarfile.open(outfile, mode) as t:
            t.add(srcdir, arcname=".")
    elif fmt == "7Z":
        py7zr = tools.require_module("py7zr")
        with py7zr.SevenZipFile(outfile, "w") as z:
            z.writeall(srcdir, ".")
    elif fmt == "RAR":
        raise ToolMissing("RAR の作成は非対応です (RAR は解凍のみ対応)。")
    else:
        raise ToolMissing(f"未対応のアーカイブ形式: {fmt}")
    return outfile


def convert_archive(infile: str, outfile: str, src: str, dst: str) -> str:
    tmp = tempfile.mkdtemp(prefix="fec_arc_")
    try:
        _extract_archive(infile, src, tmp)
        return _create_archive(tmp, outfile, dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
#  FONT
# --------------------------------------------------------------------------- #

def convert_font(infile: str, outfile: str, src: str, dst: str) -> str:
    if dst == "EOT" or src == "EOT":
        raise ToolMissing("EOT フォントの変換は本バージョンでは未対応です。")
    fontTools = tools.require_module("fontTools.ttLib", "fonttools")
    from fontTools.ttLib import TTFont
    if dst == "WOFF2" or src == "WOFF2":
        tools.require_module("brotli")  # needed by fonttools for woff2
    font = TTFont(infile)
    flavor = {"WOFF": "woff", "WOFF2": "woff2"}.get(dst, None)
    font.flavor = flavor
    font.save(outfile)
    return outfile


# --------------------------------------------------------------------------- #
#  Top-level dispatch
# --------------------------------------------------------------------------- #

_HANDLERS = {
    "画像": convert_image,
    "音声": convert_av,
    "動画": convert_av,
    "文書・テキスト": convert_document,
    "データ・コード": convert_data,
    "3Dモデル・CAD": convert_3d,
    "アーカイブ・圧縮": convert_archive,
    "フォント": convert_font,
}


def convert(infile: str, outfile: str, src_ext: str, dst_ext: str) -> str:
    """Convert ``infile`` from ``src_ext`` to ``dst_ext`` writing ``outfile``.

    Returns the path actually written (may differ from ``outfile`` for
    multi-page PDF→image, which produces a zip).  Raises ToolMissing /
    RuntimeError on failure.
    """
    src, dst = _u(src_ext), _u(dst_ext)
    cat = category_for(src, dst)
    if cat is None:
        raise ToolMissing(f"{src}→{dst} は対応表にない変換です。")
    handler = _HANDLERS[cat]
    os.makedirs(os.path.dirname(os.path.abspath(outfile)), exist_ok=True)
    return handler(infile, outfile, src, dst)
