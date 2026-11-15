# tjoy-seatmap

T・ジョイの座席選択ページを保存した **HARファイル** から、**全席空席の座席表**(PNG/SVG)を自動生成するツールです。
[toho-seatmap](../toho-seatmap-tool) と同じ使い方・同じ出力形式です。T・ジョイの座席ページの構造に合わせて、読み取り部分を作り直しています。

- 既定の **公式風** は、公式の座席図(背景画像)をそのまま使い、その上にタイトル帯と凡例を足したものです。座席は描き直しません。
- **プレーン** は、座席の位置と席種から明るい配色のベクター描画を作ります。背景画像が無い画面は、自動的にこの描画になります。
- 通信はしません (HARの中のページを読むだけ)。`--fetch-missing` を付けた時だけ、背景画像をT・ジョイのサイトから取得します。
- HARにはCookie等が含まれるため、他人へ渡す際は注意してください。

解析メモ: [docs/ANALYSIS.md](docs/ANALYSIS.md)

## 対象の劇場・画面

| 劇場 | 劇場コード | 座席表 (HAR) | スケジュール (HAR) | 備考 |
|---|---|---|---|---|
| 新宿バルト9 | 140 | スクリーン3 | 済 | 背景画像はHARに本体が無いため、現状は座席の位置から描画 |
| T・ジョイ エミテラス所沢 | 200 | スクリーン1,2,3,4,11 | 済 | 背景画像は同梱 (`tjoy_seatmap/assets/screens/`) |
| T・ジョイ梅田 | 320 | **未送付** | 済 | 座席HARが届くまで座席表は作れない |
| T・ジョイ京都 | 360 | **未送付** | 済 | 同上 |

## 取得すべきHAR

### 1. 座席表 (画面ごとに1ファイル)
座席選択ページ(`https://tjoy.jp/<劇場>/reservation/choice_seat`)を開いた状態で保存します。

1. T・ジョイの劇場ページで、座席表を見たい上映回を選ぶ。
2. 座席選択画面 (座席図が見える画面) が出たら、開発者ツールを開く (F12)。
3. **Network** タブで「**Preserve log**(ログを保存)」と「**Disable cache**(キャッシュを無効化)」にチェックを入れる。
4. ページを再読み込み (F5) する。
5. Network タブを右クリック →「**HAR としてエクスポート (コンテンツ付き)**」(Chrome: Save all as HAR with content)。
6. ファイル名は `tjoy_<館名>_<画面番号>.har` (例: `tjoy_tokorozawa_1.har`、`tjoy_shinjuku_3.har`、`tjoy_umeda_1.har`)。
   画面番号はファイル名ではなく座席図の画像から決まるので、名前は表示用です。

注意:
- 1つのHARには1画面分の座席選択ページを入れてください(複数画面を1つにまとめても読めますが、確認しやすさのため分けると安心です)。
- 座席図の本体が含まれないHAR(リダイレクトの `reservation/index/...` の302だけ等)は読めません。座席図が表示された状態で保存してください。

### 2. 劇場スケジュール (劇場ごとに1ファイル)
劇場トップ (`https://tjoy.jp/<スラッグ>`) を開いた状態で、同じ手順で HAR を保存します。
劇場名 (例: `T・ジョイ梅田`) とスクリーン名 (`シアター1` など) を取るために使います。無くても座席表は作れますが、劇場名は「T・ジョイ (コード 320)」と表示されます。

### 3. 施設案内 (劇場ごとに1ファイル・特別設備の表示に必要)
`https://tjoy.jp/<スラッグ>/facilities` を開いた状態で、同じ手順で HAR を保存します。「シアター情報」表の備考欄から、画面ごとの特別設備を読みます。
所沢のHAR(`tjoy_tokorozawa_theaters.har`)は取得済みです。新宿・梅田・京都の施設案内HARは未送付です。

### 背景画像が欠ける場合
座席図の画像は大きいため、HARの書き出し時に省略されることがあります (Fiddlerの上限、約60KB超)。その場合:
- 同梱分がある画面(所沢 1,2,3,4,11)は、同梱の背景画像を自動で使います。
- それ以外は、GUIで「不足する背景画像をT・ジョイのサイトから取得」にチェック、CLIなら `--fetch-missing` を付けると、HARのURL (`cdn.tjoy.jp/images/_up/theater/...png`) から取得してキャッシュします (この時だけ通信します)。
- 取得もできない場合は、座席の位置から描画します(公式の座席図ではなくなります)。

## 使い方

### GUI
`tjoy-seatmap-gui` を起動 → 「ファイル追加」で `.har` / `.zip` / フォルダを選択 → 「座席表を読み込む」→ プレビュー確認 → 「すべて保存」。

### CLI
```
tjoy-seatmap-cli tjoy_tokorozawa.zip -o out
tjoy-seatmap-cli tjoy_tokorozawa_1.har -f png --scale 3
tjoy-seatmap-cli tjoy_shinjuku_3.har --schedule tjoy_shinjuku_schedule.har --json
```
主なオプション: `--fetch-missing` / `-f png,svg,webp` / `--svg-objects` / `--scale` / `--style official|plain` / `--no-title` / `--no-legend` / `--schedule` / `--theater-name` / `--font` / `--json`

- `--style official` (既定): 公式の座席図そのもの + タイトル帯 + 凡例。背景が無い画面は plain になります。
- `--style plain`: 明るい配色のベクター描画。席番号入り (`--no-numbers` で番号なし)。
- 車いす席は座席図(背景)にのみ描かれます。プレーン版では席数だけ見出しに書きます。

### 出力形式
- ファイル名: `<入力名>_<スタイル>.<拡張子>`。スタイルは `plane` / `official`。
  例: `tjoy_tokorozawa_1_official.png`、`tjoy_tokorozawa_1_official_noObject.svg`、`tjoy_tokorozawa_1_plane.png`。
- `-f webp`: PNGと同じ画像をロスレスで変換したもの。
- SVG: `--svg-objects` で座席を1席ずつ選択できるオブジェクトにできます (レイヤー `layer-seats` > 行 `row-A` > 座席 `seat-A-16`、`data-row/number/kind`)。

### 劇場名
劇場コードから自動判定します (140=新宿バルト9、200=T・ジョイ エミテラス所沢、320=T・ジョイ梅田、360=T・ジョイ京都)。
それ以外は「T・ジョイ (コード …)」と表示されるので、手動で指定できます。
- GUI: 画面を選び「劇場名」欄に入力して「適用」。
- CLI: `--theater-name "200=T・ジョイ エミテラス所沢"` (コード付き) / `--theater-name "T・ジョイ ○○"` (全画面)。
- 記憶した名前は `%APPDATA%\tjoy-seatmap\theaters.json` (Linux: `~/.config/tjoy-seatmap/theaters.json`) に保存されます。

## 席種

座席ページの `type-seat` コードと `seat-group` から、次の種別に分けます (`tjoy_seatmap/seatpage.py` の `TYPE_KIND` / `kind_of`)。

| 席種コード | 種別 (凡例) | 備考 |
|---|---|---|
| 1, 5 | 一般席 | 1 で seat-group が無い席 |
| 1 + seat-group (2席) | ペアシート | 所沢4 |
| 1 + seat-group (3席) | トリオシート | 所沢4 |
| 2 | エグゼクティブシート | 所沢1・2・3 |
| 3 | プレミアシート | 所沢11 |
| 11 | リクライニングシート | 最前列。所沢1・2 |
| 14 | カウンターシート | 最後列。所沢11 |
| その他 | 席種コード N | 未確認の席種 |

席種5は、利用者がフロアマップで一般席と確認したものです。凡例の画像名 (`icn_type5`) は「車椅子スペース」ですが、座席としては一般席です。
追加料金は座席表には表示しません。

## T・ジョイの特別設備
T・ジョイで現在存在する特別設備は次のとおりです(利用者提供):
IMAX / Dolby Atmos / Dolby Cinema / ScreenX / ScreenX with Dolby Atmos / IMAXレーザー / MX4D / T-LEX。

設備は施設案内ページ(`/facilities`)の「シアター情報」表の**備考欄**から、画面ごとに読み取り、見出し帯のサブタイトルに表示します。備考の表記ゆれ(SCREENX など)は上の名称に統一します。備考に設備が2つ並ぶ場合(例: SCREENX/Dolby Atmos)は「ScreenX / Dolby Atmos」のように両方表示します。施設案内のHARが無い劇場は、表が揃っている分だけ内蔵の表から表示します(新宿バルト9 シアター6=Dolby Cinema、T・ジョイ京都 シアター9=ScreenX / Dolby Atmos。`schedule.py` の `BUILTIN_FACILITIES`)。

## インストール・開発
```
pip install -r requirements.txt
python run_cli.py …        # CLI (引数なしで GUI)
python run_gui.py          # GUI (tkinter が必要)
python -m unittest discover -s tests
```

## リリース (GitHub Actions)
`.github/workflows/build.yml` を使います。Releases で `v0.1.0` のようなタグを公開すると、Windows/Linux のビルドが添付されます (`tjoy-seatmap-v0.1.0-windows-x64.zip`、`tjoy-seatmap-v0.1.0-linux-x64.tar.gz`)。
Actions の「Run workflow」からテストビルド(Artifacts のみ)もできます。

## 背景画像・フォントについて
- `tjoy_seatmap/assets/screens/` の座席図は、T・ジョイの著作物です。**リポジトリは非公開(Private)にしてください**。公開する場合はこのフォルダを外してください(背景は無くても動作し、座席の位置からの描画になります)。
- 日本語フォント(Linux版)は `tjoy_seatmap/fonts/` に同梱します (ビルド時にNoto Sans CJKをコピー)。

## 制限
- GUIはドラッグ&ドロップ非対応 (ファイル選択ダイアログ)。
- 梅田・京都は座席HARが届くまで座席表は作れません。
- 背景画像がHARに無い画面は、座席の位置からの描画になります。
- 車いす席の位置は背景画像にだけ描かれるため、プレーン版には描きません(席数のみ表示)。
