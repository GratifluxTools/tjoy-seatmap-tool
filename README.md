# tjoy-seatmap

T・ジョイの座席選択ページを保存した **HARファイル** から、**全席空席の座席表**(PNG/SVG)を自動生成するツールです。
TOHO版(toho-seatmap)と同じ操作・同じ出力形式です。GUI と CLI の両方があります。

- 通信はしません。HARの中の座席ページ(HTML)と、記録された画像だけを読みます(HARにはCookie等が含まれるため、他人へ渡す際は注意してください)。
- 解析メモ: [docs/ANALYSIS.md](docs/ANALYSIS.md)

## 対応劇場と取得状況

| 劇場 | 座席表(HAR) | 公式の座席表画像 | 備考 |
|---|---|---|---|
| 新宿バルト9 | スクリーン3 | 未同梱(HARに画像があれば使用) | 公式風はHARに画像がある場合のみ |
| T・ジョイ エミテラス所沢 | スクリーン 1・2・3・4・11 | 同梱済み | 特別席(エグゼクティブ・プレミア・リクライニング・カウンター・ペア・トリオ)対応 |
| T・ジョイ梅田 | **未取得** | — | 座席選択画面のHARが必要 |
| T・ジョイ京都 | **未取得** | — | 座席選択画面のHARが必要 |

## 取得していただくHAR

### 必要なもの: 座席選択画面のHAR(スクリーンごとに1ファイル)
「上映回を選んで、座席を選ぶ画面が表示された状態」のHARです。**1スクリーン1ファイル**にしてください。

1. ブラウザ(Chrome / Edge)で T・ジョイの劇場ページを開き、作品と上映回を選ぶ
2. **上映回ボタンを押す前に**、開発者ツール(F12)→ **Network(ネットワーク)** タブを開き、記録を開始する
   - 上映回ボタンを押して、予約の画面(`…/reservation/index/…`)から座席選択画面(`…/reservation/choice_seat`)まで進む
   - 座席表が表示されたら、記録を止める
3. Network タブの **設定(歯車)で「Disable cache(キャッシュを無効化)」にチェック**を入れてから、もう一度 上映回ボタンを押して取り直す(キャッシュを無効化しないと、画像の本体がHARに入らないことがあります)
4. Network タブの中で右クリック →「**Save all as HAR with content**」(または「HARとしてエクスポート(コンテンツ付き)」)で保存する
5. ファイル名は `tjoy_<館名>_<スクリーン番号>.har` にすると分かりやすいです(例: `tjoy_tokorozawa_4.har`)。複数のHARをまとめてzipにしても構いません

**保存に含まれているべきもの**(含まれていないと失敗します)
- `…/reservation/index/…` への **302 リダイレクト**の記録(上映回・作品・シアター番号の情報が入っています)
- `…/reservation/choice_seat` の **座席ページ(HTML)**

### 任意: 公式の座席表画像
座席ページは、公式の座席表画像(`cdn.tjoy.jp/images/_up/theater/<劇場コード>_<番号>_<日付>.png`)を読み込みます。
HARに画像の本体が含まれていれば、そのまま公式風の画像に使います。含まれていない場合は次のどちらかで補います。
- 上の手順 3 の「キャッシュを無効化」で取り直す
- `--fetch-missing`(GUIは「不足する座席表画像をT・ジョイのサイトから取得」)を付けて実行する(通信が発生します)

### 不要になったもの
- **スケジュールのHAR**: 不要です。作品名は表示しないため、座席ページだけで十分です。
- 予約完了後の画面や、ログイン・会員情報のページ: 不要です。

### うまくいかないとき
- 「座席ページ(choice_seat)が見つかりません」→ 座席選択画面が表示された状態で保存したHARか確認してください。
- 「公式の座席表画像がありません」→ 上の「キャッシュを無効化」で取り直すか、`--fetch-missing` を使ってください。画像が無くてもプレーン表示は作れます。
- 「ページ表記と座標の件数が一致しません」→ 座席選択画面の途中で保存された可能性があります。

## 使い方

### GUI
`tjoy-seatmap-gui` を起動 → 「ファイル追加」で `.har` / `.zip` / フォルダを選択 → 「座席表を読み込む」→ プレビュー確認 → 「すべて保存」。
保存中は進捗ウィンドウ(進捗バー・現在のファイル名・件数)を表示します。「中止」を押すと、次のファイルから書き出しを止めます(保存済みのファイルは残ります)。

### CLI
```
tjoy-seatmap-cli tjoy_tokorozawa.zip -o out
tjoy-seatmap-cli tjoy_tokorozawa_4.har -f png --scale 3 --no-numbers
tjoy-seatmap-cli *.zip --json
```
主なオプション: `--fetch-missing`(公式の座席表画像をT・ジョイのサイトから取得) / `-f png,svg,webp` / `--scale` / `--style official|plain` / `--no-title` / `--no-legend` / `--svg-objects` / `--theater-name` / `--font` / `--json`

`--style official`(既定): 公式風。公式の座席表画像の上に劇場名・シアター番号・副題、下に凡例を付けます。
`plain`: 明るい配色のベクター描画(席番号入り、`--no-numbers` で番号なし)。

### 副題と設備の表示
副題は「全席空席表示 / 席数 + 車いす席数 / 特別設備」です。映画名は表示しません。特別設備は、座席ページの映画名欄の注記(【 】で囲まれたもの)から取ります。

| 注記(例) | 表示 |
|---|---|
| IMAX | IMAX® |
| Dolby Atmos | Dolby Atmos® |
| Dolby Cinema | Dolby Cinema® |
| ScreenX | ScreenX |
| ScreenX with Dolby Atmos | ScreenX with Dolby Atmos® |
| IMAX Laser / IMAXレーザー | IMAX®レーザー |
| IMAXデジタル | IMAX®デジタルシアター |
| MX4D | MX4D® |
| T-LEX | T-LEX® |

注意: 座席ページには「IMAX」としか書かれていないため、レーザーかデジタルかは区別できず、`IMAX®` と表示します。字幕などの注記は、特別設備ではないので表示しません。

### 出力形式
- ファイル名: `<入力名>_<スタイル>.<拡張子>`。スタイルは `plane`(プレーン) / `official`(公式風)。
  例: `tjoy_tokorozawa_4_plane.png`、`tjoy_tokorozawa_4_official.png`、SVGは `tjoy_tokorozawa_4_plane_hasObject.svg` / `tjoy_tokorozawa_4_plane_noObject.svg`(公式風も同様に `official_*`)。SVGの `hasObject` / `noObject` は `--svg-objects` の有無です。JSONは `<入力名>.json`。
- 公式の座席表画像が無い画面は、公式風は作らず、プレーンとして出力します(警告を表示します)。
- `-f png,svg,webp`: **WebP は PNG と同じ画像をロスレス(劣化なし)で変換**したものです。
- SVG は座席を1席ずつ選択できるオブジェクトにできます(`--svg-objects`、GUIは「座席を1席ずつオブジェクトにする(SVG)」)。構造は レイヤー(`layer-seats`) > 行(`row-A`) > 座席(`seat-A-6`、`data-row/number/kind/fee`、ツールチップ付き)。Illustrator / Inkscape / Figma などで個別に選択・色変更できます。

### 劇場名
劇場コード(座席表画像の番号)から自動判定します(新宿=140 新宿バルト9、所沢=200 T・ジョイ エミテラス所沢、梅田・京都はURLの名前から判定)。それ以外は「T・ジョイ (site コード)」と表示されるので、手動で指定できます。
- GUI: 画面一覧で画面を選び、「劇場名」欄に入力して「適用」。
- CLI: `--theater-name "200=T・ジョイ エミテラス所沢"`(コード付きはその劇場のみ)。
- 記憶した名前は `%APPDATA%\tjoy-seatmap\theaters.json`(Linux: `~/.config/tjoy-seatmap/theaters.json`)に保存されます。

### 同梱アセットの確認(exe/バイナリが正しくビルドされたか)
`tjoy-seatmap-cli --self-check` で、席種アイコン(埋め込み)・座席表画像(同梱)・フォントが読めるか確認できます。

### Pythonから直接
```
pip install -r requirements.txt
python run_cli.py …        # CLI (引数なしで GUI)
python run_gui.py          # GUI (tkinter が必要)
python -m unittest discover -s tests -p "test_*.py"
```

## 席種

| 席種 | 追加料金 | 判定(座席ページの情報) |
|---|---|---|
| 一般席 | なし | 席種コード 1 / 5 |
| ペアシート | なし | 同じ座席グループ(seat-group)の2席 |
| トリオシート | なし | 同じ座席グループの3席 |
| プレミアシート | +500円 | 席種コード 3 |
| エグゼクティブシート | +1,000円 | 席種コード 2 |
| リクライニングシート | +200円 | 席種コード 11(最前列) |
| カウンターシート | +200円 | 席種コード 14(最後列) |

車いす席は座席ページの座標に含まれないため、座席表には描かれません(人数は副題・注記に表示します)。予約済みの席も「空席」として描きます(全席空席の座席表)。

## アイコン
`assets/icon/`(`icon.svg` / `icon-1024.png` / `icon-256.png` / `icon.ico`)。TOHO版と同じ汎用デザインです。

## リリース (GitHub Actions)

ワークフローは `.github/workflows/build.yml` の1つだけです。

### 新しい版を出す(通常の手順)
1. GitHub の **Releases → Draft a new release** で、タグ名を `v0.1.0` のように入力して公開(Publish)します。
2. 公開をきっかけに Build が自動で動きます。Windows / Linux の両方をビルドして、そのRelease に添付します。
   - 添付ファイル: `tjoy-seatmap-v0.1.0-windows-x64.zip`(GUI/CLIのexe) と `tjoy-seatmap-v0.1.0-linux-x64.tar.gz`
   - タグは `v0.1.0` / `0.1.0` / `0.1.0-beta` の形式(3つの数字が必要)。
3. 失敗した場合は Actions タブのログを確認してください。修正後は、Release を削除して同じタグで作り直すと、再ビルド・添付されます。

### テストビルド(添付しない)
Actions タブ → **Build** → *Run workflow* で、対象OS(`windows` / `linux` / `both`)と版番号(空欄なら `0.0.0-dev`)を指定して実行します。成果物は Artifacts にだけ出ます。

- リポジトリは **Private** にしてください(座席表画像は T・ジョイの著作物です)。
- Windows版は `tjoy-seatmap-gui.exe` / `tjoy-seatmap-cli.exe`(Python不要の単一exe)。Linux版は `.tar.gz` を展開し、`chmod +x` のうえ実行します。
- Linux版は日本語フォント(Noto Sans CJK)を同梱します。Windows版はOS標準フォントを使います。

## 制限
- GUIはドラッグ&ドロップ非対応(ファイル選択ダイアログ)。
- 座席表画像(公式風の背景)は HAR に記録されているか、同梱分がある画面だけ公式風になります。
- 車いす席の位置は描画しません(座席ページに位置が無いため)。
- 特別設備の レーザー / デジタル は座席ページで区別できないため、`IMAX®` と表示します。
- 座席表画像・席種アイコンは T・ジョイの著作物です。**リポジトリは非公開(Private)にしてください**。
