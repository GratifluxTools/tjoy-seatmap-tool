# tjoy-seatmap

T・ジョイ（東映系）劇場の座席選択ページを保存した **HARファイル** から、**全席空席の座席表**（PNG / SVG / WebP）を自動生成するツールです。
toho-seatmap と同じく GUI と CLI の両方があります。座席ページのHTMLだけを読み、通信はしません（背景の自動取得 `--fetch-background` を除く）。

- 解析メモ: [docs/ANALYSIS.md](docs/ANALYSIS.md)

## 対応劇場

| 劇場 | 座席HAR（座席表） | スケジュールHAR | 備考 |
|---|---|---|---|
| 新宿バルト9 | スクリーン3 | あり | 劇場名・作品名は座席ページから取得 |
| T・ジョイ エミテラス所沢 | スクリーン1・2・3・4・11 | あり | 特別席（エグゼクティブ・プレミア・リクライニング・カウンター・ペア・トリオ）対応 |
| T・ジョイ梅田 | 未取得 | あり | 座席HAR待ち |
| T・ジョイ京都 | 未取得 | あり | 座席HAR待ち |

新しい劇場も、座席ページの構造が同じなら読めます（劇場名は座席ページの記載を使います）。

## 使い方

### HARの作り方
1. ブラウザで座席選択画面（`…/reservation/choice_seat`）を開く（上映回の選択から進む）
2. 開発者ツール → Network → 「HARとしてエクスポート（コンテンツ付き）」
3. スクリーンごとに1ファイル。予約リダイレクト（`reservation/index/…`、302）を含めてください。

スケジュールのHAR（劇場トップページ）は、作品名の補完に使えます（任意）。

### GUI
`tjoy-seatmap-gui` を起動 → 「ファイル追加」で `.har` / `.zip` / フォルダを選択 → 「座席表を読み込む」 → 一覧で画面を選ぶとプレビュー → 「保存」。
- 表示形式（公式風 / プレーン）を選びます。
- 公式風で使う公式画像は「公式画像フォルダから一括設定」か、画面ごとに「公式画像を設定」で指定します。
- 保存する画面は一覧の ☑（スペースキーかダブルクリックで切り替え）で選びます。

### CLI
```
# 既定: 公式風（公式画像がある画面のみ）とプレーンを両方、SVGはオブジェクトあり/なしの両方
tjoy-seatmap-cli tjoy_tokorozawa.zip --official-dir official -o out
# プレーンのみ、SVGはオブジェクトありだけ
tjoy-seatmap-cli tjoy_shinjuku_3.har -s plain --svg-objects on -o out
tjoy-seatmap-cli *.har -f png,svg,webp --scale 2
tjoy-seatmap-cli *.har --schedule tjoy_shinjuku_schedule.har --json
tjoy-seatmap-cli --self-check
```

主なオプション: `-s official,plain`（既定 両方）/ `--svg-objects on,off`（既定 両方）/ `-f png,svg,webp`（既定 `png,svg`）/ `--official-dir` / `--official` / `--scale` / `--no-title` / `--no-legend` / `--schedule` / `--json` / `--self-check`

出力ファイル名は TOHO版と同じく、**入力ファイル名（拡張子なし）** を使います（zipの中のHARなら、その名前）。
- `<入力名>_official.png` / `<入力名>_plane.png`
- `<入力名>_plane_hasObject.svg` / `<入力名>_plane_noObject.svg`
- `<入力名>_official_hasObject.svg` / `<入力名>_official_noObject.svg`

### 表示形式（-s）
- **official（公式風）**: 公式の座席表画像を中央に置き、上に劇場名・スクリーン番号・席数、下に凡例を付けます。背景色は公式画像の左上の色に合わせます。
  - PNG: 公式画像の周りに見出しと凡例を付けたもの。
  - SVG: 公式画像を埋め込み、その上に座席ごとの透明な選択用オブジェクト（`<g id="seat-A-12">`）を置きます。
  - 公式画像は、ファイル名 `tjoy_<劇場キー>_screenNN.png` か、サイトの画像名（例 `200_04_20240700.png`）で `--official-dir` に入れてください。
  - 公式画像が無い画面は飛ばして警告します。
- **plain（プレーン）**: TOHO版と同じ見た目です。席番号・行記号・SCREEN帯・凡例（席数と追加料金）を描きます。
  - PNG / WebP / SVG（SVGはレイヤー: スクリーン・座席・行記号・凡例）。

### 公式画像について
HARには公式の座席表画像の本体が含まれないことがあります（容量の上限で省かれるため）。公式風で出すには、公式の座席表画像（PNG）を用意して `--official-dir` で指定します。
公式画像の座標は座席ページの座標（`data-coords`）と同じ画素空間です。

## 席種

| 席種 | 追加料金 | 判定（座席ページの情報） |
|---|---|---|
| 通常席 | なし | 席種コード 1（幅40px）・5（幅50px・肘掛け付き） |
| ペアシート | なし | 同じ seat-group の2席 |
| トリオシート | なし | 同じ seat-group の3席 |
| プレミアシート | +500円 | 席種コード 3 |
| エグゼクティブシート | +1,000円 | 席種コード 2 |
| リクライニングシート | +200円 | 席種コード 11 |
| カウンターシート | +200円 | 席種コード 14 |

車椅子席は座席ページの座標に含まれないため描画されません（座席数の注記に人数を表示）。
予約済みの席も「空席」として描きます（全席空席の座席表）。

## 版番号・リリース（GitHub Actions）

ワークフローは `.github/workflows/build.yml` の1つです（toho-seatmap と同じ流れ）。

1. GitHub の **Releases → Draft a new release** でタグ `v0.1.0` を作って公開する
2. 公開をきっかけに Build が動き、Windows（exe）と Linux（tar.gz）を作って Release に添付します
3. テストだけ行う場合は、Actions → **Build** → Run workflow（成果物は Artifacts のみ）

## 開発者向け

```
pip install -r requirements.txt
python -m unittest discover -s tests -v
python tests/make_sample_har.py        # tests/sample/sample.har の再生成
python tools/make_icon.py --embed      # アイコン（GUI埋め込み）の再生成
python tools/set_version.py 0.1.0      # 版番号の書き換え
python run_gui.py / python run_cli.py …
```

## 注意
- 座席表は T・ジョイの著作物です。リポジトリは **非公開（Private）** にしてください。
- アイコン（`assets/icon/`）は、どの映画館チェーン版でも使える汎用デザインです。

