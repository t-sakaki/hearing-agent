# M7 マイクテスト 実行手順書（ぺいくん用）

この手順書は、ThinkPad 内蔵マイク（Microphone Array (AMD Audio Device)）を使って
**約 15〜20 秒の架空質問文を読み上げ、文字起こし→ドラフト→承認→TTS** までを一気通貫で検証するためのものです。
実事件資料は一切使用しません。有料 API も呼びません（すべて無料・ローカル）。

---

## 1. 事前準備

### 1.1 必要なターミナル
- **WSL ターミナル**（Ubuntu 等）を 1 枚開く
- 作業ディレクトリ: `/mnt/c/Users/taira/hearing-agent`

```bash
cd /mnt/c/Users/taira/hearing-agent
```

### 1.2 仮想環境の有効化（必要なら）
```bash
source /home/taira/hearing-agent-venv/bin/activate
```

### 1.3 読み上げ原稿の確認
`data/mic_script.txt` に約 15〜20 秒分の架空質問文があります。
**声に出して読む前に、一度黙読してください。**

```bash
cat data/mic_script.txt
```

**内容（再掲）:**
> 緑地保全仮許可に関する審理において、審理員の皆様にお尋ねいたします。処分庁が示した追加資料Bについて、請求人として意見を述べさせていただきます。当該処分は、緑地保全区域における仮許可の要件を満たしておらず、手続きに瑕疵があると考えます。以上です。

---

## 2. 実行コマンド（コピーして実行）

### 2.1 標準実行（対話モード・承認ゲートあり・TTSあり）
```bash
bash scripts/run_m7_mic.sh --seconds 20
```

### 2.2 非対話テスト用（stdin で承認入力）
```bash
# 承認する場合
printf 'approve\n' | bash scripts/run_m7_mic.sh --stdin --seconds 20

# 編集承認する場合
printf 'edit\n修正後の文面\nEND\n' | bash scripts/run_m7_mic.sh --stdin --seconds 20

# 却下する場合
printf 'reject\n' | bash scripts/run_m7_mic.sh --stdin --seconds 20
```

### 2.3 既存 WAV を使う（録音スキップ・検証用）
`--stdin` 単独では入力待ちのまま止まるので、必ずパイプで 1 行目に決定を渡す。

```bash
printf 'approve\n' | bash scripts/run_m7_mic.sh --input-wav data/dummy_question.wav --stdin --clear-stop
```

### 2.4 古い STOP フラグがある場合
```bash
bash scripts/run_m7_mic.sh --clear-stop --seconds 20
```

### 2.5 TTS をスキップ（承認ゲートまで）
```bash
bash scripts/run_m7_mic.sh --no-tts --seconds 20
```

---

## 3. 実行の流れと「いつ話し始めるか」

`bash scripts/run_m7_mic.sh --seconds 20` を実行すると、以下の流れで進みます。

```
=== M7 Microphone Test Started ===
Recording 20 seconds to data/mic/mic_20261111_XXXXXX.wav ...
[Windows] Recording via PowerShell -> DirectShow...
ffmpeg が起動し、ここで **録音開始** します
```

**→ この瞬間から読み上げを始めてください。**  
（ffmpeg のログが出てから約 0.5 秒後が安全です）

```
=== 録音完了 ===
File: data/mic/mic_20261111_XXXXXX.wav
Size: XXXXX bytes
Starting batch STT (with terms)...
STT completed: model=small elapsed=X.XXs
Transcript: （文字起こし結果が表示されます）

=== ドラフト（審理員向け要点整理） ===
（Gemini 無料で生成されたドラフトが表示されます）

===== ドラフト（承認ゲート） =====
（ドラフト全文）
================================
[a]pprove / [e]dit / [r]reject / STOP を入力してください。
decision>
```

**→ ここで `a` / `e` / `r` / `STOP` のいずれかを入力して Enter**

- `a` / `approve` / `yes` / `ok` → そのまま承認、TTS 生成
- `e` / `edit` → 編集モード。続けて編集文を入力、空行または `END` で確定 → TTS 生成
- `r` / `reject` / `no` / `skip` → 却下、TTS なし
- `STOP` → キルスイッチ発動、即座に中断、TTS なし

---

## 4. 承認の仕方（詳細）

### 4.1 対話モード（標準）
`--stdin` を付けない場合、M4 と同じ `src.approval.run_gate`（interactive）が使われます。
プロンプト `decision>` が出たら以下を入力：

| 入力 | 意味 | TTS |
|------|------|-----|
| `a` / `approve` / `yes` / `ok` | 承認 | あり |
| `e` / `edit` | 編集承認（次行から編集文） | あり |
| `r` / `reject` / `no` / `skip` | 却下 | なし |
| `STOP` | 強制中断 | なし |

**編集承認の例:**
```
decision> e
編集文を入力してください（空行または END で確定）:
緑地保全仮許可の要件を満たさないとして、処分庁の判断に誤りがあると指摘する。
END
```

### 4.2 非対話モード（`--stdin`）
`--stdin` を付けた場合、M4 と同じ `src.approval.run_gate`（stdin プロトコル）が使われます。
パイプで 1 行目に決定（`approve` / `a` / `edit` / `e` / `reject` / `r` / `STOP`）、編集時は 2 行目以降に編集文を渡し、空行または `END` で確定。

```bash
# 承認
printf 'approve\n' | bash scripts/run_m7_mic.sh --stdin --seconds 20

# 編集承認
printf 'edit\n修正文面\nEND\n' | bash scripts/run_m7_mic.sh --stdin --seconds 20

# 却下
printf 'reject\n' | bash scripts/run_m7_mic.sh --stdin --seconds 20
```

---

## 5. STOP（キルスイッチ）の試し方

### 5.1 対話中に `STOP` と入力
```
decision> STOP
```
→ 即座に `killed` 決定、TTS なし、ログに `kill_timestamp_jst` 記録。

### 5.2 非対話でフラグファイル作成
別ターミナルで実行中に：
```bash
touch /mnt/c/Users/taira/hearing-agent/runtime/STOP
# または
touch /mnt/c/Users/taira/hearing-agent/output/STOP
```
→ 次のチャンク/ステップで検知され即中断。

### 5.3 STOP フラグの解除
```bash
rm -f /mnt/c/Users/taira/hearing-agent/runtime/STOP /mnt/c/Users/taira/hearing-agent/output/STOP
# または次回実行時に
bash scripts/run_m7_mic.sh --clear-stop --seconds 20
```

---

## 6. 実行後に送り返すもの

テスト完了後、以下を報告してください（**録音ファイル自体は任意**、ログ抜粋で十分です）。

### 6.1 必須報告項目
1. **実行ログの抜粋**（`logs/run_m7_<timestamp>.log` の内容、または `logs/m7.log` の最後の数行）
2. **文字起こし結果**（STT 出力）
3. **ドラフト内容**
4. **承認決定**（approve / edit_approve / reject / killed 等）
5. **TTS 生成の有無とパス**（生成された場合）
6. **問題の有無**（マイク音量・ノイズ・認識精度・遅延・クラッシュ等）

### 6.2 報告例
```
=== M7 Test Report ===
Date: 2026-11-11
Command: bash scripts/run_m7_mic.sh --seconds 20

Log excerpt:
[2026-11-11T03:15:22+0900] Recording 20 seconds to data/mic/mic_20261111_031522.wav ...
[2026-11-11T03:15:43+0900] STT completed: model=small elapsed=2.34s
[2026-11-11T03:15:43+0900] Transcript: 緑地保全仮許可に関する審理において審理員の皆様にお尋ねいたします…
[2026-11-11T03:15:45+0900] Draft generated: provider=gemini model=gemini-3.5-flash-lite latency=1.87s
[2026-11-11T03:15:50+0900] Gate decision: approve
[2026-11-11T03:15:52+0900] TTS generated: output/m7_approved_20261111_031552.mp3 (0.94s)

Transcript: 緑地保全仮許可に関する審理において審理員の皆様にお尋ねいたします…
Draft: 請求人は緑地保全仮許可の要件不備と手続き瑕疵を指摘。処分庁の追加資料Bを根拠に…
Decision: approve
TTS: output/m7_approved_20261111_031552.mp3 (generated)

Issues: なし。マイク音量良好、専門用語（緑地保全仮許可/審理員/処分庁/請求人）すべて正しく認識。
```

---

## 7. 録音ファイルの削除コマンド

テスト用 WAV ファイルを削除する場合：

```bash
# 最新の mic_*.wav のみ削除
rm -f /mnt/c/Users/taira/hearing-agent/data/mic/mic_*.wav

# 特定ファイルを指定削除
rm -f /mnt/c/Users/taira/hearing-agent/data/mic/mic_20261111_031522.wav

# data/mic ディレクトリごと削除（README/keep は残したい場合は中身だけ）
rm -rf /mnt/c/Users/taira/hearing-agent/data/mic/
mkdir -p /mnt/c/Users/taira/hearing-agent/data/mic/
```

> **注意**: `data/mic/` は `.gitignore` に `data/mic/*.wav` として登録済みです。
> ディレクトリ自体と `.gitkeep` / `README.md` 等は残したまま WAV のみ削除されます。

---

## 8. トラブルシューティング

| 症状 | 確認・対処 |
|------|------------|
| `ffmpeg.exe not found` | Windows で `winget install Gyan.FFmpeg` 後、WSL を再起動 (`wsl --shutdown`) |
| 録音が始まらない / 0 バイト | Windows マイクのプライバシー設定「デスクトップ アプリのアクセス」がオンか確認 |
| 「Microphone Array (AMD Audio Device)」以外が録音される | `--device "Microphone Array (AMD Audio Device)"` を明示指定 |
| STT が英語になる | `data/terms.txt` に日本語用語があるか確認（M6 以降は既定で有効） |
| 承認ゲートでタイムアウト | `--stdin` で非対話実行、または 120 秒以内に入力 |
| `killed` になる | `runtime/STOP` または `output/STOP` が残っていないか `--clear-stop` で確認 |
| `Could not find output pin` / `I/O error` / OpenAL `0x80070005` (Access Denied) | 設定 → プライバシーとセキュリティ → マイク で「マイクへのアクセス」と「デスクトップ アプリがマイクにアクセスすることを許可」がオンか確認。別アプリがマイクを占有していないか確認。**必ず自分の対話的な WSL または PowerShell ウィンドウで実行**（リモート自動化セッションからはキャプチャが拒否されることがある） |
| WSL から録音する場合 | `record_mic.sh` を使う（内部で `powershell.exe -File` に Windows パスを渡す）。PowerShell だけで試すなら: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\Users\taira\hearing-agent\scripts\record_mic.ps1 -Seconds 20` |

---

以上。不明点があれば即座に確認してください。