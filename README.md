# PlayStation Disc Cost & Trust — article companion

Zenn論考「PlayStationはディスクを捨てて得をするのか。コストと信頼を同じ式で考えてみる」の計算用補足です。

**実在の企業の採算予測ではありません。すべてのモデル入力は説明用の仮定です。**
ディスク供給を変更するとき、追加利益・追加離脱・買い控え・移行費用が損益をどう変えるかを比較します。

## 入口

- [出力付きNotebook](analysis.ipynb)：式、設定、実行結果を順番に読む。
- [設定ファイル](code/scenarios.json)：仮想顧客群・施策・費用の前提。
- [Pythonモデル](code/model.py)と[テスト](code/test_model.py)。
- [保存結果](results/)と[図](images/ps-disc-trust/)：記事で使った条件の計算値。
- [モデルの範囲](docs/MODEL_NOTES_JA.md)：単位、入力、計算しないもの。
- [確認記録](docs/VALIDATION.md)：今回実際に再実行した範囲。
- [利用条件](RIGHTS.md)：閲覧用に公開。利用は許可制。

## 実行手順

以下は著者または必要な許可を得た方が再実行する場合の技術手順です。
権利の扱いは [RIGHTS.md](RIGHTS.md) を先に確認してください。

Python 3.10以降を対象としています。3.10・3.11・3.12・3.14で `verify_reproduction.py` が通ることを確認しました（3.13は v1.0.0 の時点で Linux・旧スクリプトで確認、v1.0.1 では未実行）。計算本体とテストに追加パッケージは不要です。

### 確認だけをする（保存結果は書き換わりません）

ルートフォルダから次を実行します。テストを流し、モデルと感度分析を一時フォルダへ書き出して、`results/` の保存結果と比べます。

```bash
python3 verify_reproduction.py
```

数値は相対誤差 1e-9 以内なら一致とみなし、文字列は完全に一致を求めます。Pythonの版による最終桁の差は許し、記事の桁（小数第2位）に出る差は見逃しません。

### 計算をやり直して保存結果を上書きする

**注意：次の `model.py`（`--out ../results` のとき）と `experiments.py` は、`results/` の保存済みファイルを上書きします。** Pythonの版によっては最終桁だけが変わり、gitに差分が出ます（値の意味は変わりません）。確認だけなら上の `verify_reproduction.py` を使ってください。`model.py` は `--out` に別のフォルダを指定すれば上書きしません。`experiments.py` は常に `results/` へ書きます。

```bash
cd code
python3 -m unittest -v
python3 model.py --config scenarios.json --out ../results
python3 experiments.py
```

### 図を再生成する

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r code/requirements-plots.txt
python3 code/charts.py
```

Windowsで仮想環境を有効にする場合は `.venv\Scripts\activate` を使います。
`code/charts.py` は `results/` の保存結果を読むだけなので、先にモデルを実行する必要はありません。
`charts.py` は `images/ps-disc-trust/` の図5枚を直接書き換えます。画素は同じでもバイト列が変わり、gitに差分が出ます。リポジトリをそのままにしたいときは、実行後に `git checkout images/` で戻してください。
図の再生成は、Python 3.11・3.12（macOS）で、`code/requirements-plots.txt` に固定した版（numpy 1.26.4・matplotlib 3.8.0）を使い、保存済みの図5枚と寸法・画素が一致することを確認しました。ファイルのバイト列までは一致しません。3.13以降では、`requirements-plots.txt` の指定が適用されず numpy・matplotlib が入らないため、実行できません。3.11か3.12で実行してください。Linuxなど他のOSも未確認です。

### Notebook

Jupyterが利用できる環境で、リポジトリのルートを作業ディレクトリとして `analysis.ipynb` を開きます。
Jupyterが未導入なら、仮想環境で `python3 -m pip install jupyterlab` の後に `jupyter lab` を起動します。
Notebook内の計算は同じ `code/model.py` を読み込みます。
億円の表示は小数第4位までです（表示だけで、値は丸めていません）。記事の数字（小数第2位）と比べるときは、この表示から一度だけ丸めてください。

### ブラウザ計算機

ZIPを展開し、`calculator.html` を開きます。同階層の `code/calculator.js` が必要です。
GitHubのファイル閲覧画面そのものはHTMLアプリの実行画面ではありません。
ローカルで表示するか、別途GitHub Pagesなどを設定してください。このフォルダを置くだけでPagesは有効になりません。
計算機はブラウザ内で計算し、入力の送信や外部APIへの通信は行いません。

## 既定値の確認例

- 簡略モデルの損益分岐：約7.44186%。
- 追加離脱5%：+10.5億円。追加離脱8%：-2.4億円。
- 同じ例で一人の追加利益を600円へ変えた場合の損益分岐：約1.97044%。

これらは予測値ではなく、付属の仮定から得た計算結果です。

## 公開範囲

このリポジトリ用フォルダには、モデル、仮定、テスト、出力付きNotebook、合成結果、生成図を含めています。
記事本文、個人の編集指示、非公開メモ、第三者の論文PDFや元記事全文は含めていません。
Sony / SIEの公式・公認の分析ではありません。

## 版の対応

元の計算パッケージの日付：2026-10-08。

- v1.0.0（2026-10-08）：記事に対応する版です。コミットは 19e730bba5bdcef8d1e4b553bebb91bfe9f74b4d です。
- v1.0.1（2026-10-10）：文書、確認スクリプト、Notebookの表示の訂正です。計算式・仮定・保存結果（`results/`）・図は v1.0.0 と同じです。変更点は [CHANGELOG](docs/CHANGELOG.md) にあります。

既定ブランチは `main` です。
