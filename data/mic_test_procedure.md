# M7 本番マイクテスト手順（ぺいくん用・短い版）

録音は、**自分で開いた WSL ターミナル**からのみ成功します（リモート自動化セッションではマイクを開けません）。ThinkPad の内蔵マイク（Microphone Array (AMD Audio Device)）を使います。有料 API は使いません。

始める前に、設定 → プライバシーとセキュリティ → マイク で「マイクへのアクセス」と「デスクトップ アプリがマイクにアクセスすることを許可」がオンか確認してください。

読み上げ原稿（`data/mic_script.txt`、架空の文です）:

> 緑地保全仮許可に関する審理において、審理員の皆様にお尋ねいたします。処分庁が示した追加資料Bについて、請求人として意見を述べさせていただきます。当該処分は、緑地保全区域における仮許可の要件を満たしておらず、手続きに瑕疵があると考えます。以上です。

---

## (1) 通しの承認テスト（読み上げ → 文字起こし → ドラフト → 承認 → TTS）

WSL を開き:

```bash
cd /mnt/c/Users/taira/hearing-agent
cat data/mic_script.txt
bash scripts/run_m7_mic.sh --seconds 20 --clear-stop
```

`[Windows] Recording via PowerShell -> DirectShow...` のあと、ffmpeg のログが出たら読み上げを始めてください（約 0.5 秒後が安全です。20 秒で録音は終わります）。

文字起こしとドラフト（複数行の全文）が表示されたら、`decision>` で:

- 承認して読み上げさせる: `a` または `approve` と入力して Enter
- 直してから承認: `e` のあと編集文、空行または `END` で確定
- 却下（TTS なし）: `r` または `reject`

承認すると `output/m7_approved_YYYYMMDD_HHMMSS.mp3` が作られ、ログにパスが出ます。

---

## (2) STOP（キルスイッチ）テスト

(1) のあと、もう一度同じ原稿を読みます。

```bash
cd /mnt/c/Users/taira/hearing-agent
bash scripts/run_m7_mic.sh --seconds 20 --clear-stop
```

ffmpeg が始まったら同様に読み上げ、ドラフトのあと `decision>` で **`STOP`** と入力して Enter。

期待する結果: 決定は `killed`、TTS は作られない（`TTS: no_tts`）、`runtime/STOP` が残ることがあります。残っていたら次を実行:

```bash
rm -f /mnt/c/Users/taira/hearing-agent/runtime/STOP /mnt/c/Users/taira/hearing-agent/output/STOP
```

別の試し方（録音中や TTS 中に別ターミナルから）:

```bash
touch /mnt/c/Users/taira/hearing-agent/runtime/STOP
```

---

## (3) 送り返してほしいもの

録音ファイルそのものは不要です。次を送ってください。

1. (1) と (2) それぞれについて、`logs/run_m7_<timestamp>.log` の抜粋（文字起こし、ドラフト全文、`decision`、`tts_path`）
2. 専門用語（緑地保全仮許可 / 審理員 / 処分庁 / 請求人）が正しく聞き取れたか
3. マイク音量・ノイズ・遅延・エラーの有無（`Could not find output pin` / `I/O error` / `0x80070005` が出たか）
4. (1) で MP3 ができたか（パス）、(2) で TTS が作られなかったか

---

## (4) 片付け

```bash
rm -f /mnt/c/Users/taira/hearing-agent/data/mic/mic_*.wav
rm -f /mnt/c/Users/taira/hearing-agent/runtime/STOP /mnt/c/Users/taira/hearing-agent/output/STOP
```

（テスト用の MP3 やログは残してかまいません。WAV だけ消してください。）
