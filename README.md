# PlayStation Disc Cost & Trust — article companion

Zenn論考「PlayStationはディスクを捨てて得をするのか——コストと信頼を同じ式で考える」の計算用補足です。

**実在の企業の採算予測ではありません。すべてのモデル入力は説明用の仮定です。**
ディスク供給を変更するとき、追加利益・追加離脱・買い控え・移行費用が損益をどう変えるかを比較します。

## 入口

- [出力付きNotebook](analysis.ipynb)：式、設定、実行結果を順番に読む。
- [設定ファイル](code/scenarios.json)：仮想顧客群・施策・費用の前提。
- [Pythonモデル](code/model.py)と[テスト](code/test_model.py)。
- [保存結果](results/)と[図](images/ps-disc-trust/)：記事で使った条件の計算値。
- [モデルの範囲](docs/MODEL_NOTES_JA.md)：単位、入力、計算しないもの。
- [確認記録](docs/VALIDATION.md)：今回実際に再実行した範囲。
- [利用条件](RIGHTS.md)：閲覧用の公開。OSSライセンスは付与していません。

## 実行手順

以下は著者または必要な許可を得た方が再実行する場合の技術手順です。
権利の扱いは [RIGHTS.md](RIGHTS.md) を先に確認してください。

Python 3.10以降を対象としています。計算本体とテストに追加パッケージは不要です。

```bash
cd code
python3 -m unittest -v
python3 model.py --config scenarios.json --out ../results
python3 experiments.py
```

計算結果を変更せず確認するには、ルートフォルダから次を実行します。

```bash
python3 verify_reproduction.py
```

### 図を再生成する

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r code/requirements-plots.txt
python3 code/charts.py
```

Windowsで仮想環境を有効にする場合は `.venv\Scripts\activate` を使います。
図の再生成前にモデル・感度分析を実行してください。

### Notebook

Jupyterが利用できる環境で、リポジトリのルートを作業ディレクトリとして `analysis.ipynb` を開きます。
Jupyterが未導入なら、仮想環境で `python3 -m pip install jupyterlab` の後に `jupyter lab` を起動します。
Notebook内の計算は同じ `code/model.py` を読み込みます。

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
記事掲載時に使用したコミットとReleaseを記事から指定すると、後日の変更と区別できます。
このフォルダの作成時点では、GitHub上のリポジトリやReleaseは作成していません。
