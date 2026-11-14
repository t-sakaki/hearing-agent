# Daytona追加の中間報告（2026年11月14日・16:45前）

## 実装
- src/daytona_citations.py：指定API URL対応の0.x AsyncDaytonaによる一時環境作成、公開出典検索だけの隔離実行、JSON結果、finallyでの削除要求。作成応答不明時は今回の一意名で環境を検索。60秒期限と削除用10秒を分ける。
- src/rebuttal_pipeline.py：出典取得先の任意切替とJSTログへの実行先・削除状態の記録。
- scripts/run_tavily_demo.py：--sandbox local/daytona とWebからの指定に対応。
- hanron-server.mjs、hanron-live.js、hanron.html：出典取得先選択と実行先の表示。ローカル切替後の検索・生成が続けられるよう応答期限を120秒に調整。
- requirements-daytona.txt：任意のSDK依存を分離。指定API URLに対応する0.231.0を使用。
- scripts/test_daytona_pipeline.py、README.md：単体検証と実行手順。

## 確認
- Tavilyの8件とDaytonaの9件、合計17件が合格。
- 作成・実行成功時の削除、実行失敗・不正応答・タイムアウトでの削除、作成応答不明時の検索と削除、削除失敗の警告、キーなしのローカル切替、転送内容の限定をモックで確認。
- --sandbox daytonaでキーなしのCLI実行がローカルへ切り替わり正常終了。
- この作業環境には両キーがなく、Tavilyの実通信、Daytonaでの実作成・検索・削除は未確認。SDKの実環境導入も未確認。Tavily実通信を確認してからDaytonaを有効化する。

## データと削除
転送対象は出典検索コード、固定論点ID、Tavilyキーのみ。案件フォルダ・発言・案件抜粋・LLMキーを渡さない。キー値・リモート生ログ・例外原文を表示しない。
finallyで削除を要求するが、管理API障害や強制終了時の残存までは保証できない。削除確認の失敗は画面に明示して管理画面での確認を案内する。削除成功表示はdelete要求受理であり、クラウド上での削除完了の実証ではない。

## 提出時の扱い
Daytonaは「コード統合済み・実機確認待ち」。Tavilyは先行レポートに記載の実通信未確認状態を引き継ぐ。実機で動いた技術だけを「使用」と記載。Nosanaは未導入・未使用のまま。mainへのmerge、commit、push、公開、フォーム送信は行っていない。


API URL訂正：利用者指定 https://app.daytona.io/api に合わせ、SDKを0.231.0へ変更。0.xのcreate/process.exec/deleteを使用。通常削除に加えてephemeralと3分TTLを設定。環境変数DAYTONA_API_URLで同じURLを指定可能。実接続は未確認。
