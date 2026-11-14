"""文字またはWAVから出典確認、反論生成、本人承認、Edge TTSへ。"""
import argparse
import json
import sys
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.rebuttal_pipeline import prepare
from src.killswitch import is_stop_requested, jst_now_str

def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group()
    g.add_argument("--text")
    g.add_argument("--wav")
    p.add_argument("--context-file",default=str(ROOT/"data/sample_case.md"))
    p.add_argument("--topic",choices=["reasons","partial","existence"],default="reasons")
    p.add_argument("--sandbox",choices=["local","daytona"],default="local")
    p.add_argument("--no-llm",action="store_true")
    p.add_argument("--no-tts",action="store_true")
    p.add_argument("--json-stdio",action="store_true")
    args=p.parse_args()
    if args.json_stdio:
        d=json.load(sys.stdin)
        result=prepare(str(d.get("statement", ""))[:6000],str(d.get("context", ""))[:24000],d.get("topic","reasons"),bool(d.get("useLlm",False)),ROOT,sandbox=d.get("sandbox","local"))
        print(json.dumps(result,ensure_ascii=False));return 0
    statement=args.text
    if args.wav:
        from src.stt import transcribe
        statement=transcribe(Path(args.wav),use_terms=True)[0]
    if not statement:
        statement=input("処分庁の発言：").strip()
    result=prepare(statement,Path(args.context_file).read_text(encoding="utf-8"),args.topic,not args.no_llm,ROOT,sandbox=args.sandbox)
    print("時刻（JST）：",jst_now_str())
    print("反論案：",result["draft"] or "不明（生成未実施または失敗）")
    print("手元資料の参照（モデル出力・要照合）：",result.get("local_citations",[]))
    print("外部出典：",result["sources"].get("message","不明"))
    for c in result["sources"]["citations"]:
        print(c["id"],c["title"],c["url"],"\n",c["excerpt"] or c["snippet"])
    print("要確認：",result.get("unknowns",[]))
    if not result["draft"] or args.no_tts or is_stop_requested(ROOT):return 0
    from src.approval import run_gate
    gate=run_gate(result["draft"],mode="interactive",project_root=ROOT)
    if gate.decision not in ("approve","edit_approve") or not gate.final_text or is_stop_requested(ROOT):return 0
    # TTSは子プロセスで実行し、生成中もSTOPを監視する。
    from src.tts_speak import make_output_path
    out=make_output_path(ROOT/"output",tag="tavily_approved")
    code="import sys; from src.tts_speak import speak_to_file; speak_to_file(sys.stdin.read(),sys.argv[1])"
    proc=subprocess.Popen([sys.executable,"-c",code,str(out)],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,text=True,encoding="utf-8")
    proc.stdin.write(gate.final_text);proc.stdin.close()
    started=time.monotonic()
    while proc.poll() is None:
        if is_stop_requested(ROOT) or time.monotonic()-started>40:
            proc.terminate();proc.wait();print("音声生成を停止しました");return 0
        time.sleep(.1)
    if proc.returncode:print("音声生成失敗。本人が表示文を読み上げてください。");return 0
    from src.playback import play_audio_file
    print("読み上げ：",play_audio_file(out,ROOT))
    return 0
if __name__=="__main__":
    try:raise SystemExit(main())
    except KeyboardInterrupt:raise SystemExit(130)
    except Exception:print("処理できません。資料パスと実行環境を確認してください。",file=sys.stderr);raise SystemExit(1)
