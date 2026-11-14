"""ローカルSTT常駐ワーカー。音声をメモリー内で処理し保存しない。"""
import base64,io,json,sys,wave

def emit(data):
    print(json.dumps(data,ensure_ascii=False),flush=True)

def main():
    import numpy as np
    from faster_whisper import WhisperModel
    # 既存smallモデルを使用。初回はモデルの読込に時間がかかる。
    model=WhisperModel("small",device="cpu",compute_type="int8")
    emit({"ready":True})
    for line in sys.stdin:
        request={}
        try:
            request=json.loads(line)
            raw=base64.b64decode(request["audio"],validate=True)
            if len(raw)>1000000:raise ValueError()
            with wave.open(io.BytesIO(raw),"rb") as w:
                if w.getnchannels()!=1 or w.getsampwidth()!=2 or w.getframerate()!=16000:raise ValueError()
                audio=np.frombuffer(w.readframes(w.getnframes()),dtype="<i2").astype(np.float32)/32768.0
            if audio.size>16000*15:raise ValueError()
            language="en" if request.get("language")=="en" else "ja"
            segments,_=model.transcribe(audio,language=language,beam_size=1,vad_filter=True,initial_prompt="情報公開、存否応答拒否、部分開示、理由提示、処分庁、審理員")
            text="".join(s.text for s in segments).strip()
            emit({"id":request.get("id"),"text":text})
        except Exception:
            emit({"id":request.get("id"),"error":"音声を処理できませんでした。文字入力を利用してください。"})
if __name__=="__main__":
    try:main()
    except Exception:emit({"fatal":True,"error":"ローカルSTTを起動できません。Python環境を確認してください。"})
