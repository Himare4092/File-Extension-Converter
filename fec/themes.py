# -*- coding: utf-8 -*-
"""Color themes applied via Qt stylesheets."""
from __future__ import annotations

THEMES = {
    "system": "Windows のデフォルト",
    "white": "ホワイト",
    "amoled": "AMOLED ブラック",
}

_WHITE = """
QWidget { background-color: #ffffff; color: #202124; }
QMainWindow, QDialog, QMenuBar, QMenu, QMessageBox { background-color: #ffffff; }
QPushButton { background-color: #f1f3f4; color: #202124; border: 1px solid #dadce0;
              border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { background-color: #e8eaed; }
QPushButton:checked { background-color: #1a73e8; color: #ffffff; border-color: #1a73e8; }
QPushButton:disabled { color: #9aa0a6; }
QListWidget { background-color: #ffffff; border: 1px solid #dadce0; }
QListWidget::item:selected { background-color: #1a73e8; color: #ffffff; }
QLineEdit, QComboBox { background: #ffffff; border: 1px solid #dadce0;
                       border-radius: 4px; padding: 4px; color: #202124; }
QComboBox QAbstractItemView { background: #ffffff; color: #202124;
                              selection-background-color: #1a73e8; selection-color: #ffffff; }
QProgressBar { border: 1px solid #dadce0; background: #ffffff; text-align: center; }
QProgressBar::chunk { background-color: #1a73e8; }
QMenuBar::item:selected { background: #e8eaed; }
QMenu { border: 1px solid #dadce0; }
QMenu::item:selected { background: #1a73e8; color: #ffffff; }
QScrollArea { border: none; }
"""

_AMOLED = """
QWidget { background-color: #000000; color: #e8eaed; }
QMainWindow, QDialog, QMenuBar, QMenu, QMessageBox { background-color: #000000; }
QPushButton { background-color: #1a1a1a; color: #ffffff; border: 1px solid #333333;
              border-radius: 6px; padding: 6px 10px; }
QPushButton:hover { background-color: #2a2a2a; }
QPushButton:checked { background-color: #0a84ff; color: #ffffff; border-color: #0a84ff; }
QPushButton:disabled { color: #666666; }
QListWidget { background-color: #0a0a0a; border: 1px solid #222222; }
QListWidget::item:selected { background-color: #0a84ff; color: #ffffff; }
QLineEdit, QComboBox { background: #111111; border: 1px solid #333333;
                       border-radius: 4px; padding: 4px; color: #e8eaed; }
QComboBox QAbstractItemView { background: #0a0a0a; color: #e8eaed;
                              selection-background-color: #0a84ff; selection-color: #ffffff; }
QProgressBar { border: 1px solid #333333; background: #111111; text-align: center; }
QProgressBar::chunk { background-color: #0a84ff; }
QMenuBar::item:selected { background: #1a1a1a; }
QMenu { border: 1px solid #333333; }
QMenu::item:selected { background: #0a84ff; color: #ffffff; }
QScrollArea { border: none; }
"""


def apply_theme(app, theme: str) -> None:
    """Apply ``theme`` to the QApplication. 'system' restores the native look."""
    if theme == "white":
        app.setStyleSheet(_WHITE)
    elif theme == "amoled":
        app.setStyleSheet(_AMOLED)
    else:  # system / unknown -> native Windows style
        app.setStyleSheet("")
