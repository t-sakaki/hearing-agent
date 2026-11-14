# Tokyo AgentForge 提出文面（最終版 v3）

- 作成：2026-11-14（v2 14:55 JST を基に最終化）
- 用途：提出フォーム https://tinyurl.com/20261114submission へコピーする文面
- パートナー技術は **Tavily**（コード実装済み：`hanron-core.mjs` の `searchSources()`、`src/tavily_citations.py` の `citations_for_topic()` 等）。Daytona / Nosana は提出文に「使用」とは書かない
- 個人情報・事件番号・APIキーは含まない
- リポジトリ: https://github.com/t-sakaki/hearing-agent

---

## 日本語

**プロジェクト名**

反論エージェント（Hanron Agent）

**一行説明（100文字以内）**

行政に「ノー」と言われたとき、Tavilyで集めた公式出典付きの反論案を出し、本人が承認した文だけを読み上げる補佐AI。

**詳細説明（約300文字）**

市役所から「できません」と言われたとき、弁護士を頼めない多くの市民は、その場で根拠を持って言い返せません。反論エージェントは、処分庁の主張を入力すると、Tavilyで公式サイト（go.jp、lg.jp、自治体）に限定して根拠を検索し、出典URL付きの反論ドラフトを出します。見つからない根拠は「不明」と出し、作り上げません。生成後は本人が承認・修正・却下し、承認した文だけが読み上げられます。いつでもSTOPで即停止できます。2026年11月20日に安城市役所で行う口頭意見陳述での使用を予定しています。

**使用したパートナー技術**

Tavily。反論ドラフトの根拠となる条例・判例・公的資料を、公式ドメインに限定した Search / Extract で収集し、出典（タイトル・URL・抜粋）をドラフトに添えるために使用。実装は `hanron-core.mjs` の `searchSources()` と `src/tavily_citations.py` の `citations_for_topic()`。

---

## English

**Project name**

Hanron Agent (反論エージェント)

**One-line description (within 100 Japanese characters)**

行政に「ノー」と言われたとき、Tavilyで集めた公式出典付きの反論案を出し、本人が承認した文だけを読み上げる補佐AI。

**Detailed description (about 300 characters)**

When city hall says "no," most people cannot hire a lawyer or answer with sources on the spot. Hanron Agent takes the disposal authority's claim as input, searches for supporting evidence with Tavily restricted to official domains (go.jp, lg.jp, municipal sites), and produces a rebuttal draft with cited sources. Evidence it cannot find is marked "unknown," never invented. The person then approves, edits, or rejects the draft, and only the approved text is read aloud. A STOP switch halts everything at any time. It is planned for use at an oral hearing at Anjo City Hall on 20 November 2026.

**Partner technology used**

Tavily. It collects the ordinances, court cases, and public documents behind the draft via Search / Extract restricted to official domains, and attaches citations (title, URL, snippet) to the draft. Implemented in `searchSources()` in `hanron-core.mjs` and `citations_for_topic()` in `src/tavily_citations.py`.

---

## フォームへ貼る前のチェック

- [x] 一行説明は100文字以内
- [x] 詳細説明は約300文字
- [x] パートナー技術は Tavily のみ（Daytona / Nosana / CodeAF は「使用」と書いていない）
- [x] APIキー・個人情報・事件番号を含めていない
- [x] 実装済み機能のみを「動く」と書いた（実API疎通はキー設定済み端末での確認前提）
- [ ] デモURLが確定したら記入（未確定なら空欄または「ローカルデモ」）
- [ ] 送信前に本人が全文を確認
