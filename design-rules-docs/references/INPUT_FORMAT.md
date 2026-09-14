# 入力形式

最上位は `title`、`slides`、任意の `theme`。未定義キーは拒否します。JSONにコメントは使えません。全例はexample.jsonを参照してください。

```json
{
  "title": "資料名",
  "theme": "neutral",
  "slides": [
    {
      "type": "text",
      "title": "一枚の主題",
      "message": "このページで伝えること。",
      "items": ["一つ目の根拠", "二つ目の根拠"]
    }
  ]
}
```

最上位titleは80文字、slidesは1〜80枚。themeはneutral / mono / red / olive。表紙以外はtitle（32文字以内）とmessage（70文字以内）が必須。source（160文字以内）は任意。ただしグラフとcausalの図では必須です。

| type | 追加必須キー | 制限・任意キー |
|---|---|---|
| cover | subtitle | titleは48文字、subtitleは80文字。metaは1〜4個の60文字以内の文字列。messageは指定しない |
| text | items | 1〜5個、各80文字以内 |
| sections | groups | 1〜3個の `{heading, items}`。heading24文字、items1〜2個・各65文字 |
| compare | columns | 2個の `{heading, items}`。heading24文字、items1〜4個・各45文字 |
| flow | steps, relation | steps2〜4個・各36文字。relationはsequence / causal |
| cycle | steps, relation | steps3〜4個・各14文字。relationはsequence / causal。最後から最初へ戻る |
| hierarchy | root, children | root30文字、children2〜4個・各36文字。階層は1段 |
| table | headers, rows | headers2〜5個・各20文字、rows1〜6行・列数一致。セル文字列40文字以内または数値。alignは列数分のleft / right。stripedは真偽値 |
| image | image, alt, caption | imageは相対パス、alt200文字、caption90文字。itemsは任意・1〜3個・各70文字。annotationsは任意・最大3個の `{x, y, label}`、xとyは0〜1、label28文字 |
| bar | labels, values, unit, source | labels1〜8個・各10文字、valuesは同数の数値。unit12文字。errorsは任意、同数の0以上の対称誤差 |
| line | labels, series, unit, source | labels2〜8個・各12文字。series1〜3個の `{name, values}`。name12文字・重複不可、valuesは時点数と一致。unit12文字 |
| pie | labels, values, unit, source | labels2〜5個・各14文字。valuesは同数の正の値。unit12文字 |
| scatter | points, x_label, y_label, source | points2〜16個の `{x, y, label}`、label10文字。軸名は各24文字、単位も含める |

数値は有限、絶対値1兆以下。NaN、Infinity、真偽値の数値代用を禁止。文字列の絵文字・装飾記号・改行などの制御文字を禁止。任意のURL画像は読み込まず、入力JSONのフォルダ外の画像にもアクセスしません。PNG/JPEG/WebP、1枚15MB・4000万画素以下。

文字数上限は入力検証用です。列数や文字幅によっては、その範囲内でも表示検査に失敗します。その際は文章を減らすかページを分けてください。例えば8時点の長いラベルは、短い年・月名へ整理します。

## 画像の例

```json
{
  "type": "image",
  "title": "製品の全体像",
  "message": "本体と操作部分の対応を示します。",
  "image": "assets/product.png",
  "alt": "製品の正面写真。右側に操作パネルがある。",
  "caption": "図1：製品の正面。",
  "annotations": [{"x": 0.8, "y": 0.45, "label": "操作パネル"}],
  "source": "出典：利用者提供の製品写真"
}
```

座標は表示枠ではなく画像自体に対する割合。左上が0,0、右下が1,1。例のパスや説明は実際の素材に合わせて変更します。

## エラーへの対応
入力エラーはページ番号付きで標準エラーへ表示し、終了コード1で停止します。生成済みのHTMLを入力エラーで上書きしません。構造検査のみは `--validate-only`。表示検査はHTMLを開くかverify.cjsで行います。
