# 反論エージェント / Hanron Agent

行政不服審査請求の口頭意見陳述に向けて、処分庁の主張に対する反論ドラフトを、出典付きで作成・確認できる補佐AIです。2026年11月20日 14:00、安城市役所での口頭意見陳述での使用を想定して開発しています。

Hanron Agent is an assistant AI that drafts sourced rebuttal arguments (反論ドラフト) against the disposal authority's (処分庁) claims, in preparation for an oral statement (口頭意見陳述) at Anjo City Hall on 20 November 2026, 14:00.

---

## 日本語

### 解決する問題

市役所から「できません」と言われたとき、弁護士を頼めない多くの市民は、条例や審査基準をその場で読んで根拠を持って言い返すのが難しい。Hanron Agent は、専門家がいなくても、ひとりの市民が根拠を持って言い返せるようにする補佐AIである。

### 動作の流れ

1. **入力** — 処分庁の主張（口頭意見陳述で言われたこと）を文字で入力する
2. **Tavily検索** — 公式ドメイン（go.jp / lg.jp / 安城市など）に限定して Search / Extract し、出典候補（タイトル・URL・抜粋）を集める。見つからなければ「不明」と出す（作り上げない）
3. **反論ドラフト** — 手元の案件資料と出典候補から、短い反論案を生成する
4. **本人承認** — 承認 (approve) / 修正 (edit) / 却下 (reject) のゲートを通す。**承認するまで音は出ない**
5. **読み上げ** — 承認された文だけを読み上げる
6. **STOPスイッチ** — いつでも即停止。停止フラグ（`runtime/STOP`）で生成・読み上げを止め、ログは日本時間で残す

### Tavily を使っているファイルと関数（実装済み）

| ファイル | 関数 / 経路 | 役割 |
|---|---|---|
| `hanron-core.mjs` | `officialUrl()` / `searchSources()` | ブラウザー・サーバー版デモの出典検索。Tavily Search API を公式ドメイン限定（`include_domains` + `restrict`）で呼び、8秒タイムアウト、結果URLを `officialUrl()` で再検査。キー未設定・失敗・公式結果なしのときはサンプル出典へフォールバック |
| `hanron-server.mjs` | `GET /api/search` | 上記 `searchSources()` を呼ぶHTTP経路 |
| `src/tavily_citations.py` | `citations_for_topic()` / `_post()` / `official()` | Search → Extract の2段で公式出典候補と本文抜粋を取得。ドメイン制限・HTTPS検査・失敗時「不明」返し |
| `src/daytona_citations.py` | `collect_citations()` | 上記をローカル、または Daytona sandbox 内で実行する切替 |
| `src/rebuttal_pipeline.py` | `prepare()` | STOP確認 → 出典収集（Tavily）→ ドラフト生成 → JSTログ記録までの共通経路 |
| `scripts/run_tavily_demo.py` / `scripts/test_tavily_pipeline.py` | — | 動作確認・テストスクリプト |

APIキーは環境変数 `TAVILY_API_KEY` からのみ読む。キーの値をコード・ファイル・提出文に書かない。本人の入力文・案件名・手元資料はTavilyへ送らず、公開論点の検索語だけを送る。

### 実行方法

Node.js 22以降。追加パッケージは不要。

```bash
npm start
```

http://localhost:3030/ を開く。Tavilyキーが未設定のままでも、事前保存済みの公的資料とサンプル出典で動く（外部通信なしのオフライン実演も可能）。

Tavilyキーを使う場合は、サーバー起動前に同じシェルで環境変数 `TAVILY_API_KEY` を設定する（値はファイルに書かない）。

### デモURL

【デモURL】（デプロイURLが確定したら記入。ローカルでは `npm start` で http://localhost:3030/）

リポジトリ: https://github.com/t-sakaki/hearing-agent

### 範囲の明示

- 準備度表示は語句照合に基づく確認項目であり、勝率や法的正しさの点数ではない
- 出典は候補であり、主張の正しさを証明しない。条例・判例の適用判断は本人が行う
- 音声合成（読み上げ）は承認後の文に限る。審理の場で声を使うときは、行政不服審査法第31条の補佐人として審理員の許可が前提

---

## English

### The problem it solves

When city hall says "no," most people cannot hire a lawyer or read an ordinance on the spot to answer with sources. Hanron Agent helps a single citizen talk back with evidence, without an expert.

### How it works

1. **Input** — the agency's claim is entered as text
2. **Tavily search** — Search / Extract restricted to official domains (go.jp / lg.jp / City of Anjo, etc.) collects citation candidates (title, URL, snippet). Nothing found is reported as "unknown," never invented
3. **Rebuttal draft** — a short draft is generated from the case file and the citation candidates
4. **Human approval** — an approve / edit / reject gate. **No audio is produced until approval**
5. **Read aloud** — only the approved text is spoken
6. **STOP switch** — stops generation and playback at once via a stop flag (`runtime/STOP`); logs are kept in JST

### Files and functions that use Tavily (implemented)

| File | Function / route | Role |
|---|---|---|
| `hanron-core.mjs` | `officialUrl()` / `searchSources()` | Source search for the browser/server demo. Calls the Tavily Search API restricted to official domains (`include_domains` + `restrict`), 8-second timeout, re-validates result URLs with `officialUrl()`. Falls back to sample sources when the key is missing, the call fails, or no official result is returned |
| `hanron-server.mjs` | `GET /api/search` | HTTP route that calls `searchSources()` |
| `src/tavily_citations.py` | `citations_for_topic()` / `_post()` / `official()` | Two-step Search → Extract for official citation candidates and excerpts. Domain restriction, HTTPS checks, and "unknown" on failure |
| `src/daytona_citations.py` | `collect_citations()` | Runs the above locally or inside a Daytona sandbox |
| `src/rebuttal_pipeline.py` | `prepare()` | Common path: STOP check → citation gathering (Tavily) → draft generation → JST logging |
| `scripts/run_tavily_demo.py` / `scripts/test_tavily_pipeline.py` | — | Demo and test scripts |

The API key is read only from the `TAVILY_API_KEY` environment variable and is never written into code, files, or the submission text. The user's input, case name, and local files are not sent to Tavily — only search terms about public issues.

### How to run

Node.js 22 or later. No extra packages required.

```bash
npm start
```

Open http://localhost:3030/. It also works without a Tavily key, using pre-collected public sources and sample citations (an offline demo with no external calls is available). To use Tavily, set the `TAVILY_API_KEY` environment variable in the same shell before starting the server.

### Demo URL

【Demo URL】(to be filled in once the deployment URL is confirmed; locally, `npm start` serves http://localhost:3030/)

Repository: https://github.com/t-sakaki/hearing-agent

### Scope notes

- The readiness indicator is a checklist based on phrase matching, not a score of winning odds or legal correctness
- Citations are candidates, not proof of a claim; the person makes the legal judgment
- Speech synthesis covers only approved text. Use of the voice at a hearing is premised on examiner permission for an assistant under Article 31 of the Administrative Complaint Review Act
