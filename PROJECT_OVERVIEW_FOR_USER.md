# IMC Prosperity 4 Project Overview

このファイルは、このリポジトリを進めるうえで重要な情報を、ユーザー向けに手早く確認できる形でまとめたものです。

最終更新: 2026-04-16

## 1. まず結論

- このコンテストには、各 Round ごとに `Algorithmic Challenge` と `Manual Challenge` がある。
- `Algorithmic` は Python の `Trader` を提出して戦う本戦。
- `Manual` は別枠の手動チャレンジで、`Algorithmic Challenge PnL` には影響しない。
- ただし dashboard の `Leaderboard` には `Overall` / `Algorithmic` / `Manual` の 3 種類の見方がある。
- Round 2 終了時点で `200,000 XIRECs` を確保できると、Rounds 3-5 に進める。
- wiki の表現上、この `200,000 XIRECs` は「総量」と読むのが自然で、dashboard では `Overall` を最重要表示として扱っている。

## 2. Algorithmic と Manual の違い

### Algorithmic Challenge

- 毎 Round、Python の `Trader` クラスを提出する。
- Round 終了時点で、最後に正常処理されていて `active` な提出物が採点対象になる。
- Algorithm は Prosperity の bot と取引する。
- Round 2 では `bid()` メソッドも必要。

### Manual Challenge

- 毎 Round、Algorithmic と並行して存在する別チャレンジ。
- こちらも Round 終了時点の最終提出が処理される。
- Tutorial Round では Manual は inactive。
- Manual は Algorithmic の損益に影響しない。

### 実務上の理解

- `Algorithmic` は主戦場。
- `Manual` は独立した追加得点源。
- したがって、アルゴ改善の優先度を下げてまで Manual に時間を使うのは基本的に非推奨。

## 3. XIRECs は Algorithmic と Manual の合算か

### wiki で明記されていること

- `Manual Challenges have no effect on your algorithmic trade`
- `Leaderboard` には以下の 3 表示がある:
  - `Overall`: total PnL per team
  - `Algorithmic`: algorithmic trading performance only
  - `Manual`: manual trading performance only

### そこからの実務上の解釈

`Round 2 までに 200,000 XIRECs` の進出条件は、かなり高い確度で `Overall` ベース、つまり `Algorithmic + Manual の合計` だと考えてよいです。

理由:

- Storyline では単に `secure at least 200,000 XIRECs by the end of trading Round 2` と書かれており、`algorithmic only` とは書かれていない。
- Dashboard 説明では `Overall ranking` が最重要表示として説明されている。
- `Algorithmic` と `Manual` は別タブで内訳確認できる一方、全体の進捗確認としては `Overall` が自然。

### ただし注意

wiki 内で `進出判定は Overall を使う` と 1 行で断定している箇所までは、この repo 内では見つかっていません。

なので、厳密には次のように扱うのが安全です。

- 日常運用では `Overall >= 200,000` を目標にする
- ただし意思決定の中心は引き続き `Algorithmic` に置く
- もし dashboard 上に進出条件の専用表示が出たら、その表示を最優先で確認する

## 4. Dashboard で何を見ればよいか

### 最優先で見る場所

#### Outpost View

- チーム名
- `PnL indicator`
- `overall rank on the leaderboard`

ここが、今の総合進捗を最も手早く見る場所。

### 詳しく確認する場所

#### Leaderboard

`Outpost View` から `Leaderboard` に飛べる。

見るべきタブ:

- `Overall`
  - 総 PnL を確認する場所
  - 進出条件 `200,000 XIRECs` の確認は、まずここを見るのが自然
- `Algorithmic`
  - アルゴ部分だけの成績確認
  - 実力評価や改善判断はここが重要
- `Manual`
  - Manual の成績だけ確認
  - おまけ得点源として見る

#### Mission Control

- Round ごとの提出操作の中心
- `Algorithmic Challenge` の `Challenge Details` から:
  - Data Capsule
  - Upload Algorithm
  - 過去アップロード
  - debug logs
  を確認できる

### 実務フロー

Round の進捗確認は次の順がよいです。

1. `Outpost View` で現在の PnL と overall rank をざっと確認
2. `Leaderboard > Overall` で総 PnL を確認
3. `Leaderboard > Algorithmic` で本戦の実力を確認
4. `Mission Control > Algorithmic Challenge > Challenge Details` で提出物と debug log を確認

## 5. Round の進み方とゲート

### 構造

- Tutorial Round
  - 練習用
  - 何度でもテスト可能
- Round 1
  - 2026-04-14 12:00 CEST 開始
  - 2026-04-17 12:00 CEST 締切
- Round 2
  - 2026-04-17 12:00 CEST 開始
  - 2026-04-20 12:00 CEST 締切
- Intermission
- Round 3-5
  - Round 2 の結果次第で進む後半戦

### 進出条件

- Round 2 終了時点で `200,000 XIRECs` 以上
- これを満たすと Rounds 3-5 へ進出

### Round ごとの突破条件はあるか

結論として、現時点で確認できている明示的なゲートは `Round 2` のみです。

- `Tutorial Round`
  - 練習用
  - 突破条件なし
- `Round 1`
  - 単独の足切り条件は見当たらない
- `Round 2`
  - `200,000 XIRECs` が明示された進出ゲート
  - ここを超えると Rounds 3-5 に進める
- `Round 3-5`
  - この repo 内で確認できた範囲では、追加の突破条件は見当たらない
  - 最終順位の確定フェーズと考えるのが自然

つまり、実務上は「Round ごとに脱落する」というより、
`Round 1-2 = 第1フェーズ`
`Round 3-5 = 第2フェーズ`
と理解するのがよいです。

### 賞金との関係

- `Round 2` 突破そのものに独立した賞金がある、とは確認できていない
- 賞金は最終 leaderboard ベース
- したがって `Round 2` の突破は「賞金獲得」ではなく「後半戦への参加権」

## 6. この repo で重要なファイル

### 競技で直接使う

- `src/trader.py`
  - 提出対象の本体
- `src/datamodel.py`
  - 公式 datamodel
  - 基本的に触らない
- `submissions/round1/`
  - 提出済み・提出候補アーカイブ

### 開発で使う

- `backtesting/simulator.py`
  - ローカル検証用
- `backtesting/data/`
  - dashboard から取ってきた CSV
- `tests/`
  - pytest

### 方針メモ

- `PLAN.md`
  - 全体の進め方
  - Gate 条件として `>= 200,000 XIRECs by end of Round 2`
- `LESSONS.md`
  - ラウンドをまたいだ学び
- `SKILLS.md`
  - 戦略アイデアや分析メモ
- `CLAUDE.md`
  - 実装・提出・制約の要点

### Dashboard から保存した実行物

- `artifacts/round1/dashboard_exports/`
  - dashboard から取得した Round 1 の提出コード、結果 JSON、詳細ログを保存
  - 現在は `176266` 系の 3 ファイルを `round1_*` という名前で格納済み

## 7. 提出運用で特に大事なこと

- Upload しただけでは不十分で、`active` にしないと採点対象にならない
- Round 終了後は、その Round の提出物は変更できない
- Round 2 では `Trader.bid()` が必要
- 許可ライブラリ以外を使うと silent failure の可能性がある
- `run()` は 900ms 未満で終える必要がある
- `traderData` は 50,000 chars 上限

## 8. 開発の優先順位

### 最重要

- `Algorithmic` の PnL を伸ばす
- Round 1 と Round 2 の合計でゲートを超える

### 毎 Round の基本手順

1. A.R.I.A. Uplink を見る
2. Data Capsule を取得する
3. CSV を見て商品特性を判断する
4. 商品ごとに戦略を決める
5. ローカル backtest
6. `src/trader.py` を提出
7. dashboard で `active` 化
8. test result / debug log を見て改善

## 9. 既存メモから特に重要な学び

- platform の test は full scoring と同じではない
- ローカル simulator は保守的で、platform 実績をやや過小評価する
- 強いトレンド商品に遅い EMA を fair value として使うと負けやすい
- position limit 超過は silent cancel を招く
- 複雑化より、先に CSV の単純分析をしたほうが勝ちやすい

## 10. 現時点での運用方針

- 進出判定の確認は `Outpost View` と `Leaderboard > Overall` を見る
- 戦略改善の判断は `Leaderboard > Algorithmic` と debug log を見る
- `Manual` は余力があるときの追加得点源として扱う
- ただし、もし後日 dashboard 上に `mission success` や `qualified for next phase` の明示表示が出たら、その表示を最優先の正として扱う

## 11. 出典

主な出典:

- `Prosperity 4 Wiki/Game Mechanics Overview 88b06678c18583e99158012ababd477f.md`
- `Prosperity 4 Wiki/FAQ d8506678c18583e8bc5481ce29a2ced6.md`
- `Prosperity 4 Wiki/Storyline 9a206678c1858201a47081165de0b732.md`
- `Prosperity 4 Wiki/Round Schedule 4b806678c18583299a1f81df8c824f1c.md`
- `CLAUDE.md`
- `PLAN.md`
- `LESSONS.md`
