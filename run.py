# -*- coding: utf-8 -*-
"""Launch the File Extension Converter GUI:  python run.py

Run ``run.py --selftest`` to verify the bundled conversion engine works
(used to smoke-test the packaged .exe). Exits 0 on success, 1 on failure.
"""
import sys


def _selftest() -> int:
    import os, json, tempfile
    from fec import engine
    d = tempfile.mkdtemp(prefix="fec_selftest_")
    try:
        j = os.path.join(d, "a.json")
        open(j, "w", encoding="utf-8").write(json.dumps({"k": "値", "n": 1}, ensure_ascii=False))
        engine.convert(j, os.path.join(d, "a.yaml"), "JSON", "YAML")
        from PIL import Image
        p = os.path.join(d, "i.png")
        Image.new("RGBA", (8, 8), (1, 2, 3, 255)).save(p)
        engine.convert(p, os.path.join(d, "i.jpg"), "PNG", "JPEG")
        print("SELFTEST OK: JSON->YAML, PNG->JPEG succeeded in frozen app")
        return 0
    except Exception as e:  # noqa
        print(f"SELFTEST FAILED: {e!r}")
        return 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    from fec.main import main
    main()
