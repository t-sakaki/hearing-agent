"""架空劇場専用。キー不要の既存Edge TTS。本文を保存しない。"""
import asyncio,base64,json,sys
VOICES={"office":"ja-JP-KeitaNeural","male":"en-US-AndrewMultilingualNeural","female":"ja-JP-NanamiNeural","assistant":"en-US-AvaMultilingualNeural"}
async def main():
    import edge_tts
    data=json.load(sys.stdin)
    role=data.get("role")
    if role not in VOICES:raise ValueError()
    voices=VOICES if data.get("language")!="en" else {"office":"en-US-GuyNeural","male":"en-US-AndrewMultilingualNeural","female":"en-US-JennyNeural","assistant":"en-US-AvaMultilingualNeural"}
    if role=="assistant":voices={**voices,"assistant":"en-US-AvaMultilingualNeural" if data.get("assistantVoice")=="Gacrux" else "en-US-BrianMultilingualNeural"}
    text=str(data.get("text",""))[:500]
    audio=bytearray()
    async def synthesize():
        async for item in edge_tts.Communicate(text,voices[role],rate="+0%").stream():
            if item["type"]=="audio":audio.extend(item["data"])
            if len(audio)>2000000:raise ValueError()
    await asyncio.wait_for(synthesize(),timeout=12)
    if not audio:raise ValueError()
    print(json.dumps({"audio":base64.b64encode(audio).decode(),"voice":voices[role],"provider":"Edge TTS","mime":"audio/mpeg"}))
if __name__=="__main__":
    try:asyncio.run(main())
    except Exception:print(json.dumps({"error":"Edge TTSを利用できません。端末の音声へ切り替えます。"}))
