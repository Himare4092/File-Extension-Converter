# -*- coding: utf-8 -*-
"""File Extension Converter - Windows GUI (PySide6).

Layout mirrors the requested design:
    [ 画像 ][ 音声 ][ 動画 ] ...        <- category tabs (top)
    +-----------------+   変換元ファイル  [アップロード]
    | 変換元→変換先   |          |
    | (一覧, xlsx順)  |          v
    |                 |   変換後ファイル  [ダウンロード]
    +-----------------+
"""
from __future__ import annotations

import os
import sys
import tempfile

from PySide6.QtCore import Qt, QThread, QStandardPaths, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from . import APP_NAME, __version__
from .conversions_data import CATEGORIES, PAIRS
from . import engine, settings, themes, updater
from .tools import ToolMissing


def _downloads_dir() -> str:
    d = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)
    return d or os.path.join(os.path.expanduser("~"), "Downloads")


# group pairs by category, preserving xlsx order
PAIRS_BY_CATEGORY: dict[str, list[tuple[str, str, str]]] = {c: [] for c in CATEGORIES}
for _cat, _s, _d, _dir in PAIRS:
    PAIRS_BY_CATEGORY[_cat].append((_s, _d, _dir))


class ConvertWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, infile, outfile, src, dst):
        super().__init__()
        self.infile, self.outfile, self.src, self.dst = infile, outfile, src, dst

    def run(self):
        try:
            produced = engine.convert(self.infile, self.outfile, self.src, self.dst)
            self.finished_ok.emit(produced)
        except ToolMissing as e:
            self.failed.emit(e.message)
        except Exception as e:  # noqa
            self.failed.emit(f"変換に失敗しました:\n{e}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 620)

        self.settings = settings.load()
        self._build_menu()

        self.input_path: str | None = None
        self.cur_src: str | None = None
        self.cur_dst: str | None = None
        self.cur_dir: str | None = None
        self.worker: ConvertWorker | None = None

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 12, 14, 12)
        outer.setSpacing(10)

        title = QLabel(APP_NAME)
        tf = QFont()
        tf.setPointSize(16)
        tf.setBold(True)
        title.setFont(tf)
        outer.addWidget(title)

        # ---- category tab bar (scrollable horizontally) ----
        tab_scroll = QScrollArea()
        tab_scroll.setWidgetResizable(True)
        tab_scroll.setFixedHeight(52)
        tab_scroll.setFrameShape(QFrame.NoFrame)
        tab_host = QWidget()
        tab_row = QHBoxLayout(tab_host)
        tab_row.setContentsMargins(0, 0, 0, 0)
        tab_row.setSpacing(6)
        tab_row.setAlignment(Qt.AlignLeft)
        self.tab_group = QButtonGroup(self)
        self.tab_group.setExclusive(True)
        for i, cat in enumerate(CATEGORIES):
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setMinimumHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, c=cat: self.select_category(c))
            self.tab_group.addButton(btn, i)
            tab_row.addWidget(btn)
        tab_scroll.setWidget(tab_host)
        outer.addWidget(tab_scroll)

        # ---- main split: pair list (left) | convert flow (right) ----
        split = QHBoxLayout()
        split.setSpacing(14)
        outer.addLayout(split, 1)

        left = QVBoxLayout()
        left.setSpacing(4)
        self.list_label = QLabel("変換可能な拡張子（カテゴリを選択）")
        left.addWidget(self.list_label)
        self.pair_list = QListWidget()
        self.pair_list.setMinimumWidth(300)
        self.pair_list.itemClicked.connect(self.select_pair)
        left.addWidget(self.pair_list, 1)
        split.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(8)
        split.addLayout(right, 1)

        self.sel_label = QLabel("変換: 未選択")
        sf = QFont()
        sf.setBold(True)
        self.sel_label.setFont(sf)
        right.addWidget(self.sel_label)

        # upload box
        self.drop = DropArea(self.set_input_file)
        right.addWidget(self.drop, 1)
        up_btn = QPushButton("変換元ファイルを選択 / アップロード")
        up_btn.clicked.connect(self.choose_input)
        right.addWidget(up_btn)

        arrow = QLabel("↓")
        arrow.setAlignment(Qt.AlignCenter)
        af = QFont()
        af.setPointSize(20)
        arrow.setFont(af)
        right.addWidget(arrow)

        self.dl_btn = QPushButton("変換してダウンロード（保存）")
        self.dl_btn.setMinimumHeight(40)
        self.dl_btn.clicked.connect(self.convert_and_save)
        right.addWidget(self.dl_btn)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        right.addWidget(self.progress)

        self.status = QLabel("カテゴリと変換ペアを選び、ファイルを指定してください。")
        self.status.setWordWrap(True)
        right.addWidget(self.status)

        # select first category by default
        if CATEGORIES:
            self.tab_group.button(0).setChecked(True)
            self.select_category(CATEGORIES[0])

    # ----- category / pair selection -----
    def select_category(self, cat: str):
        self.list_label.setText(f"変換可能な拡張子 ［{cat}］（元 → 先）")
        self.pair_list.clear()
        for s, d, direction in PAIRS_BY_CATEGORY[cat]:
            mark = "⇄" if direction.startswith("双方向") else "→"
            item = QListWidgetItem(f"{s}  {mark}  {d}      （{direction}）")
            item.setData(Qt.UserRole, (s, d, direction))
            self.pair_list.addItem(item)

    def select_pair(self, item: QListWidgetItem):
        s, d, direction = item.data(Qt.UserRole)
        self.cur_src, self.cur_dst, self.cur_dir = s, d, direction
        self.sel_label.setText(f"変換: {s} → {d}")
        self._refresh_status()

    # ----- input file -----
    def choose_input(self):
        path, _ = QFileDialog.getOpenFileName(self, "変換元ファイルを選択")
        if path:
            self.set_input_file(path)

    def set_input_file(self, path: str):
        self.input_path = path
        self.drop.show_file(os.path.basename(path))
        self._refresh_status()

    def _refresh_status(self):
        msgs = []
        if self.cur_src:
            msgs.append(f"選択した変換: {self.cur_src} → {self.cur_dst}")
        if self.input_path:
            ext = os.path.splitext(self.input_path)[1].lstrip(".").upper()
            msgs.append(f"入力: {os.path.basename(self.input_path)}")
            if self.cur_src and ext and ext != self.cur_src and not (
                    self.cur_src in {"動画全般"}):
                msgs.append(f"⚠ 入力の拡張子(.{ext})が選択した変換元({self.cur_src})と異なります。")
        self.status.setText("\n".join(msgs) or "カテゴリと変換ペアを選んでください。")

    # ----- menu / settings / about -----
    def _build_menu(self):
        bar = self.menuBar()
        m_settings = bar.addMenu("設定")
        act = m_settings.addAction("設定...")
        act.triggered.connect(self.open_settings)
        m_help = bar.addMenu("ヘルプ")
        act_about = m_help.addAction("このアプリについて")
        act_about.triggered.connect(self.open_about)

    def open_settings(self):
        dlg = SettingsDialog(self, self.settings)
        if dlg.exec() == QDialog.Accepted:
            self.settings = dlg.result_settings()
            settings.save(self.settings)
            themes.apply_theme(QApplication.instance(), self.settings["theme"])

    def open_about(self):
        AboutDialog(self, self.settings).exec()

    # ----- convert -----
    def convert_and_save(self):
        if not self.cur_src or not self.cur_dst:
            QMessageBox.warning(self, APP_NAME, "左の一覧から変換ペアを選択してください。")
            return
        if not self.input_path:
            QMessageBox.warning(self, APP_NAME, "変換元ファイルを選択してください。")
            return
        base = os.path.splitext(os.path.basename(self.input_path))[0]
        suggested = f"{base}.{self.cur_dst.lower()}"
        if self.settings.get("ask_every_time", True):
            out, _ = QFileDialog.getSaveFileName(
                self, "変換後ファイルの保存先", suggested,
                f"{self.cur_dst} (*.{self.cur_dst.lower()});;すべて (*.*)")
            if not out:
                return
        else:
            save_dir = self.settings.get("default_save_dir") or _downloads_dir()
            try:
                os.makedirs(save_dir, exist_ok=True)
            except OSError:
                save_dir = _downloads_dir()
                os.makedirs(save_dir, exist_ok=True)
            out = os.path.join(save_dir, suggested)
        self._set_busy(True)
        self.status.setText(f"変換中… {self.cur_src} → {self.cur_dst}")
        self.worker = ConvertWorker(self.input_path, out, self.cur_src, self.cur_dst)
        self.worker.finished_ok.connect(self._on_ok)
        self.worker.failed.connect(self._on_fail)
        self.worker.start()

    def _set_busy(self, busy: bool):
        self.progress.setVisible(busy)
        self.dl_btn.setEnabled(not busy)

    def _on_ok(self, produced: str):
        self._set_busy(False)
        self.status.setText(f"✅ 完了: {produced}")
        QMessageBox.information(self, APP_NAME, f"変換が完了しました:\n{produced}")

    def _on_fail(self, msg: str):
        self._set_busy(False)
        self.status.setText("❌ " + msg.splitlines()[0])
        QMessageBox.critical(self, APP_NAME, msg)


class SettingsDialog(QDialog):
    def __init__(self, parent, current: dict):
        super().__init__(parent)
        self.setWindowTitle("設定")
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)

        # --- theme ---
        lay.addWidget(self._heading("カラー（テーマ）"))
        self.theme_combo = QComboBox()
        self._theme_keys = list(themes.THEMES.keys())  # system / white / amoled
        for key in self._theme_keys:
            self.theme_combo.addItem(themes.THEMES[key], key)
        cur_theme = current.get("theme", "system")
        if cur_theme in self._theme_keys:
            self.theme_combo.setCurrentIndex(self._theme_keys.index(cur_theme))
        lay.addWidget(self.theme_combo)

        # --- save location ---
        lay.addWidget(self._heading("保存場所"))
        self.ask_chk = QCheckBox("ダウンロードのたびに保存場所を確認する")
        self.ask_chk.setChecked(current.get("ask_every_time", True))
        self.ask_chk.toggled.connect(self._sync_dir_enabled)
        lay.addWidget(self.ask_chk)

        row = QHBoxLayout()
        self.dir_edit = QLineEdit(current.get("default_save_dir", "") or _downloads_dir())
        self.dir_edit.setPlaceholderText("既定の保存先フォルダ")
        self.browse_btn = QPushButton("参照...")
        self.browse_btn.clicked.connect(self._browse)
        row.addWidget(QLabel("既定の保存先:"))
        row.addWidget(self.dir_edit, 1)
        row.addWidget(self.browse_btn)
        lay.addLayout(row)
        self._sync_dir_enabled(self.ask_chk.isChecked())

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _heading(self, text):
        lbl = QLabel(text)
        f = QFont()
        f.setBold(True)
        lbl.setFont(f)
        return lbl

    def _sync_dir_enabled(self, ask: bool):
        # default-dir controls are only relevant when NOT asking every time
        self.dir_edit.setEnabled(not ask)
        self.browse_btn.setEnabled(not ask)

    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "既定の保存先を選択", self.dir_edit.text())
        if d:
            self.dir_edit.setText(d)

    def result_settings(self) -> dict:
        return {
            "theme": self.theme_combo.currentData(),
            "ask_every_time": self.ask_chk.isChecked(),
            "default_save_dir": self.dir_edit.text().strip(),
        }


class _UpdateCheckWorker(QThread):
    found = Signal(object)   # (tag, asset_url, html_url)
    failed = Signal(str)

    def __init__(self, repo):
        super().__init__()
        self.repo = repo

    def run(self):
        try:
            self.found.emit(updater.check(self.repo))
        except updater.UpdateError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa
            self.failed.emit(f"アップデート確認に失敗しました: {e}")


class _UpdateDownloadWorker(QThread):
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            self.done.emit(updater.download(self.url))
        except updater.UpdateError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa
            self.failed.emit(f"ダウンロードに失敗しました: {e}")


class AboutDialog(QDialog):
    def __init__(self, parent, app_settings: dict | None = None):
        super().__init__(parent)
        self._settings = app_settings or {}
        self._chk: _UpdateCheckWorker | None = None
        self._dl: _UpdateDownloadWorker | None = None
        self.setWindowTitle("このアプリについて")
        self.setMinimumWidth(340)
        lay = QVBoxLayout(self)
        lay.setSpacing(8)
        lay.setContentsMargins(24, 20, 24, 20)

        name = QLabel(APP_NAME)
        nf = QFont()
        nf.setPointSize(15)
        nf.setBold(True)
        name.setFont(nf)
        name.setAlignment(Qt.AlignCenter)
        lay.addWidget(name)

        ver = QLabel(f"バージョン {__version__}")
        ver.setAlignment(Qt.AlignCenter)
        lay.addWidget(ver)

        made = QLabel("Made by @FlawlessEditz01")
        made.setAlignment(Qt.AlignCenter)
        lay.addWidget(made)

        lay.addSpacing(6)
        self.update_btn = QPushButton("アップデートを確認")
        self.update_btn.clicked.connect(self.check_update)
        lay.addWidget(self.update_btn)

        self.update_status = QLabel("")
        self.update_status.setAlignment(Qt.AlignCenter)
        self.update_status.setWordWrap(True)
        lay.addWidget(self.update_status)

        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        lay.addWidget(btns)

    # ----- update flow -----
    def check_update(self):
        self.update_btn.setEnabled(False)
        self.update_status.setText("確認中…")
        self._chk = _UpdateCheckWorker(updater.get_repo(self._settings))
        self._chk.found.connect(self._on_checked)
        self._chk.failed.connect(self._on_update_error)
        self._chk.start()

    def _on_checked(self, result):
        tag, asset_url, html_url = result
        if tag and updater.is_newer(tag, __version__):
            if asset_url:
                self.update_status.setText(f"新しいバージョン {tag} をダウンロード中…")
                self._dl = _UpdateDownloadWorker(asset_url)
                self._dl.done.connect(self._on_downloaded)
                self._dl.failed.connect(self._on_update_error)
                self._dl.start()
            else:
                self.update_btn.setEnabled(True)
                self.update_status.setText(
                    f"新しいバージョン {tag} がありますが、インストーラーが見つかりません。")
                QMessageBox.information(
                    self, APP_NAME,
                    f"新しいバージョン {tag} が公開されています。\n{html_url or ''}")
        else:
            self.update_btn.setEnabled(True)
            self.update_status.setText("最新バージョンです")
            QMessageBox.information(self, APP_NAME, "最新バージョンです。")

    def _on_downloaded(self, path: str):
        self.update_status.setText("インストーラーを起動します…")
        try:
            updater.launch_installer(path)
        except Exception as e:  # noqa
            self._on_update_error(f"インストーラーの起動に失敗しました: {e}")
            return
        QMessageBox.information(
            self, APP_NAME,
            "アップデートのインストーラーを起動します。\n"
            "画面の指示に従ってインストールしてください。アプリを終了します。")
        QApplication.instance().quit()

    def _on_update_error(self, msg: str):
        self.update_btn.setEnabled(True)
        self.update_status.setText("❌ " + msg)
        QMessageBox.warning(self, APP_NAME, msg)


class DropArea(QFrame):
    """A drag-and-drop / placeholder box for the source file."""

    def __init__(self, on_file):
        super().__init__()
        self.on_file = on_file
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(120)
        # Border only; text color is left to the active theme so it stays
        # readable on the white / AMOLED black themes too.
        self.setStyleSheet(
            "QFrame{border:2px dashed #9aa0a6; border-radius:10px;}"
            "QLabel{border:none;}")
        lay = QVBoxLayout(self)
        self.label = QLabel("ここに変換元ファイルをドラッグ＆ドロップ\nまたは下のボタンで選択")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        lay.addWidget(self.label)

    def show_file(self, name: str):
        self.label.setText(f"📄 {name}")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls:
            self.on_file(urls[0].toLocalFile())


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    themes.apply_theme(app, settings.load().get("theme", "system"))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
