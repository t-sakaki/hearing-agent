"""保存済みの架空英語TTSでローカルSTTを検証。音声とキーは出力しない。"""
import base64,io,json,subprocess,sys,wave
from pathlib import Path
import numpy as np
p=Path(__file__).resolve().parents[1]
with wave.open(str(p/"runtime/google-office-check.wav"),"rb") as w:
    rate=w.getframerate();x=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float32)
size=int(len(x)*16000/rate)
x=np.interp(np.linspace(0,len(x)-1,size),np.arange(len(x)),x).astype("<i2")
buf=io.BytesIO()
with wave.open(buf,"wb") as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000);w.writeframes(x.tobytes())
proc=subprocess.Popen([sys.executable,"-u","scripts/hearing_stt_worker.py"],cwd=p,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding="utf-8")
try:
    ready=json.loads(proc.stdout.readline());assert ready.get("ready")
    proc.stdin.write(json.dumps({"id":1,"language":"en","audio":base64.b64encode(buf.getvalue()).decode()})+"\n");proc.stdin.flush()
    result=json.loads(proc.stdout.readline());text=result.get("text","")
    assert "fictional" in text.lower() or "demonstration" in text.lower(),"Transcript not matched"
    print(json.dumps({"model":"faster-whisper small","result":"passed","characters":len(text)}))
finally:proc.terminate();proc.wait(timeout=10)
