# File Extension Converter

ファイル拡張子コンバーター（Windows 版）。
`対応拡張子変換ペア一覧.xlsx` に記載された **187 ペア / 8 カテゴリ** の変換に対応します。

> Android 版は今後対応予定（下記「Android 対応」参照）。本リポジトリはまず Windows 版です。

> ⚠️WARNING!!!このプロジェクトはデバッグにClaudeを使用しています。⚠️

## 画面構成

```
File Extension Converter
[ 画像 ][ 音声 ][ 動画 ][ 文書・テキスト ][ データ・コード ][ 3Dモデル・CAD ] ...   ← 上部カテゴリタブ
┌─────────────────────┐   変換: JPEG → PNG
│ 変換可能な拡張子［画像］ │   ┌───────────────────────────┐
│  JPEG ⇄ PNG  （双方向）│   │ ここにドラッグ＆ドロップ      │  ← 変換元ファイル
│  JPEG ⇄ WebP （双方向）│   └───────────────────────────┘
│  HEIC → JPEG （単方向）│            ↓
│  ...（xlsx の順番）   │   [ 変換してダウンロード（保存）]  ← 変換後ファイル
└─────────────────────┘
```

- 上部のタブ＝大分類。クリックすると左側に「変換元 → 変換先」が **xlsx の順番どおり** に展開されます。
- `⇄` は双方向、`→` は単方向。一覧の行をクリックすると変換内容が確定します。
- 変換元ファイルをドラッグ＆ドロップ（またはボタンで選択）し、「変換してダウンロード」で保存します。

## カテゴリ別ペア数

| カテゴリ | ペア数 | 変換エンジン |
|---|---|---|
| 画像 | 46 | Pillow（+ pillow-heif / rawpy / cairosvg / imageio / Ghostscript） |
| 音声 | 34 | FFmpeg（MIDI のみ FluidSynth が必要） |
| 動画 | 37 | FFmpeg |
| 文書・テキスト | 29 | LibreOffice / PyMuPDF / openpyxl / markdown / Calibre |
| データ・コード | 10 | 純 Python（追加エンジン不要） |
| 3Dモデル・CAD | 17 | trimesh（FBX/3DS は Assimp、STEP/IGES/DWG は CAD ツール） |
| アーカイブ・圧縮 | 8 | 標準ライブラリ + py7zr（RAR は解凍のみ） |
| フォント | 6 | fonttools（EOT を除く） |

## 設定（メニュー「設定」）

- **カラー（テーマ）**: `Windows のデフォルト` / `ホワイト` / `AMOLED ブラック`（即時反映）
- **保存場所**: 「ダウンロードのたびに保存場所を確認する」のオン/オフ。オフ時は **既定の保存先フォルダ** に自動保存（未設定なら Downloads）
- 設定は `%APPDATA%\FileExtensionConverter\settings.json` に保存され、次回起動時に復元

## このアプリについて & アップデート（メニュー「ヘルプ」）

「このアプリについて」にアプリ名・バージョン・`Made by @FlawlessEditz01` を表示します。
「**アップデートを確認**」ボタンで GitHub Releases を参照し:

- 新しいバージョンがあれば **インストーラーをダウンロードしてウィザードを起動**（アプリは終了）
- 無ければ「**最新バージョンです**」と表示

更新の取得先リポジトリは `fec/updater.py` の `DEFAULT_REPO`（既定: `Himare4092/File-Extension-Converter`）。
設定ファイルの `update_repo` で上書きできます。

> **公開手順**: GitHub の `Himare4092/File-Extension-Converter` にリリース（タグ例 `v0.3.0`）を作成して
> `FileExtensionConverter-Setup-x.y.z.exe` をアセットとして添付してください。アプリは
> タグ名と現在のバージョンを比較し、新しければそのアセットを取得します。リリース未作成の間は
> 「公開されているリリースが見つかりませんでした」と表示されます。

## セットアップ

```powershell
cd "D:\My Apps Save\4\FileExtensionConverter"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 外部エンジン（カテゴリにより別途インストール）

pip だけでは音声・動画・Office 文書などは変換できません。必要に応じて入れてください。

| エンジン | 必要なカテゴリ | 入手 |
|---|---|---|
| **FFmpeg** | 音声・動画すべて | `winget install ffmpeg` または https://www.gyan.dev/ffmpeg/builds/ |
| **LibreOffice** | DOCX/XLSX/PPTX/ODT/PDF など | https://www.libreoffice.org/ |
| **Ghostscript** | EPS / AI のラスタライズ | https://ghostscript.com/ |
| **Calibre** | EPUB / MOBI / AZW3 | https://calibre-ebook.com/ |
| **Inkscape**（任意） | AI ↔ SVG/EPS | https://inkscape.org/ |
| **Assimp**（任意） | 3D の FBX / 3DS | https://www.assimp.org/ |

アプリは PATH と一般的なインストール先を自動検出します。エンジンが無い変換を実行すると、
何を入れればよいかを日本語で表示します（クラッシュしません）。

## 起動

```powershell
python run.py
```

## exe 化（配布用）

専用の spec ファイル `FileExtensionConverter.spec` を用意済みです（エンジンが `importlib`
で遅延インポートする PIL / yaml / xmltodict / toml / markdown / openpyxl などを hidden-import
として明示し、インストール済みの任意ライブラリも自動で取り込みます）。

```powershell
pip install pyinstaller
python -m PyInstaller --noconfirm --clean FileExtensionConverter.spec
```

- 出力: `dist\File Extension Converter\File Extension Converter.exe`（onedir 形式・約 330MB）
- **配布時はフォルダ `dist\File Extension Converter\` を丸ごと**（zip 等で）渡してください。exe 単体では動きません。
- 動作確認: `".\dist\File Extension Converter\File Extension Converter.exe" --selftest`
  → `SELFTEST OK ...` と表示されればエンジンは正常です。

単一 exe にしたい場合は spec の `COLLECT(...)` を削除し `EXE(...)` を onefile 構成
（`exclude_binaries=False` + `a.binaries, a.datas` を EXE に渡す）に変更します。
起動は遅くなりますが 1 ファイルになります。

> ※ FFmpeg / LibreOffice / Ghostscript / Calibre などの外部エンジンは exe に同梱されません。
> これらが必要な変換（音声・動画・Office 文書など）は、利用環境に別途インストールが必要です
> （未導入時はアプリが必要なものを日本語で案内します）。

## インストーラー作成（セットアップ exe）

[Inno Setup](https://jrsoftware.org/isdl.php) 用のスクリプト `installer.iss` を用意済みです。
PyInstaller の onedir 出力（`dist\File Extension Converter\`）を 1 つのセットアップ exe にまとめます。

```powershell
# 1) 先に exe をビルド
python -m PyInstaller --noconfirm --clean FileExtensionConverter.spec
# 2) Inno Setup を導入（未インストールの場合）
winget install --id JRSoftware.InnoSetup -e
# 3) インストーラーをコンパイル
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
```

- 出力: `installer_output\FileExtensionConverter-Setup-0.1.0.exe`（約 92MB・単一ファイル）
- **ユーザー単位インストール**（管理者権限・UAC 不要）。インストール先は `%LOCALAPPDATA%\Programs\File Extension Converter`
- スタートメニュー・（任意で）デスクトップにショートカットを作成、アンインストーラー同梱
- 日本語／英語のウィザード対応

### サイレントインストール / アンインストール
```powershell
# 無人インストール
.\installer_output\FileExtensionConverter-Setup-0.1.0.exe /VERYSILENT /NORESTART
# アンインストール
& "$env:LOCALAPPDATA\Programs\File Extension Converter\unins000.exe" /VERYSILENT
```

> バージョンを上げるときは `installer.iss` の `MyAppVersion` を更新してください。

## Android 対応（今後）

変換エンジンの中心は FFmpeg・LibreOffice などのデスクトップ前提ツールのため、Android では
構成を変える必要があります。想定パターン：

1. **共通エンジンをサーバ化**：本 `fec.engine` を API 化し、Android はアップロード/ダウンロードのみ。
2. **モバイルネイティブ**：Flutter/Kotlin + `ffmpeg_kit`（音声・動画）など、端末内で完結できる範囲を実装。

GUI（タブ＋一覧＋アップロード/ダウンロード）と対応表（`fec/conversions_data.py`）はそのまま再利用できます。

## 構成

```
FileExtensionConverter/
├─ run.py                    # 起動エントリ
├─ requirements.txt
├─ README.md
└─ fec/
   ├─ __init__.py
   ├─ conversions_data.py    # xlsx から自動生成（187 ペア / 8 カテゴリ・順序保持）
   ├─ tools.py               # 外部エンジン / ライブラリ検出
   ├─ engine.py              # 変換ルーティング + 各カテゴリのハンドラ
   └─ main.py                # PySide6 GUI
```
