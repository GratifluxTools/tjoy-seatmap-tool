# T・ジョイ 座席表・スケジュールの表示方法 (HAR解析メモ)

確認した画面: エミテラス所沢(座席: スクリーン1,2,3,4,11)、新宿バルト9(座席: スクリーン3)、
およびスケジュール(劇場トップ)HAR。梅田・京都は劇場トップのみ確認(座席HARは未取得)。

## 座席ページ
- URL: `https://tjoy.jp/<劇場スラッグ>/reservation/choice_seat`。日程・スクリーンを選ぶと、`reservation/index/<上映ID>/<スクリーンコード>/<スクリーン番号>/<日付>?type=film` を経て表示される。
- 座席図は `<img usemap="#image-map" src="https://cdn.tjoy.jp/images/_up/theater/<劇場コード>_<画面番号2桁>_<日付>.png">` の画像。画像には空席状態の座席・車いす席・通路・非常口・行記号がすでに描かれている。
- 座席は `<map name="image-map">` の `<area>`。1席=1 area。
  - `id="A-12"` (行-番号)
  - `data-coords="x1,y1,x2,y2"` (背景画像の画素座標・矩形。背景の natural size と一致)
  - `type-seat="<席種コード>"`
  - `class="seat-select"` (選択可) / `class="sold-out"` (販売済み。全席空席表示では無視)
- 車いす席は `area` にならず、背景画像に描かれるのみ。席数はモーダルの `<p>334席 +（車椅子6席）</p>` に書かれる。

### 席種コード (利用者確認の表 + 配置)
| コード | 種別 | 追加料金(参考) | 所在 |
|---|---|---|---|
| 1 | 一般席 (seat-groupなし) | 0 | 新宿3、所沢全館 |
| 5 | 一般席 | 0 | 所沢全館 (利用者確認済み) |
| 2 | エグゼクティブシート | +1000 | 所沢1・2・3 |
| 3 | プレミアシート | +500 | 所沢11 |
| 11 | リクライニングシート (最前列) | +200 | 所沢1・2 |
| 14 | カウンターシート (最後列) | +200 | 所沢11 |
| 1 + seat-group | ペアシート(2席) / トリオシート(3席) | 0 | 所沢4 (グループ 01〜06 が2席、07〜13 が3席) |

凡例の画像名 `icn_type5` は「車椅子スペース」と書かれているが、座席としての5は一般席。

ページのJS(`select-seat.js`)は席種コードごとに使う画像を決めている (1,6,10→seat1、2,3→seat4、5,14→seat5、11→seat7)。
売り切れ表示はこのJSがオーバーレイで描くもので、背景画像には含まれない。

## 背景画像
- HARの書き出し時、Fiddler の上限(約60KB超)を超えた画像は本体が省略される (`comment: Body length exceeded ...`)。
  所沢の背景画像はほぼ全て省略された。背景は同梱分(`assets/screens/200_NN.png`)か、`--fetch-missing` でURLから取得する。
- 同梱分は利用者が保存したseat-varietyページの `map_01..12.png` (`theater/200/map_XX.png` と同一内容)。

## 劇場とスクリーン名
- 劇場名: 劇場トップ `https://tjoy.jp/<スラッグ>` の `<title>` (例: `T・ジョイ エミテラス所沢`)。
- スクリーン名: 劇場トップのリンク `<a data-target="#screen09">シアター９</a>` (番号と表示名)。
- 劇場コード: 背景画像のファイル名先頭 (`140`=新宿バルト9, `200`=エミテラス所沢, `320`=梅田, `360`=京都)。

## 特別設備
- 施設案内ページ(`/<スラッグ>/facilities`)の「シアター情報」表 (`table.table-information`) の行が、画面ごとに
  `<a data-target="#screenNN">シアター N</a>` と備考(`<td>`の3列目)を持つ。備考に設備名が入る
  (所沢: 1=Dolby Atmos、2=IMAXレーザー、3=SCREENX、他は空)。「SCREENX/Dolby Atmos」は ScreenX with Dolby Atmos を指す。
- 備考の表記は利用者提供の名称に統一する (SCREENX→ScreenX)。対象: IMAX / Dolby Atmos / Dolby Cinema / ScreenX / ScreenX with Dolby Atmos / IMAXレーザー / MX4D / T-LEX。
- スケジュール(劇場トップ)HARには、この表は無い。

## スケジュール(劇場トップ)
- 劇場トップのHTMLに、上映回・スクリーン一覧が入る。API(JSON)は使わない。
