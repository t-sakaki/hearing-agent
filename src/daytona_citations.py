"""Daytonaへ送るのは公開検索コード・論点ID・Tavilyキーだけ。"""
import asyncio
import json
import os
import signal
import shlex
from types import SimpleNamespace
import uuid
from pathlib import Path
from .tavily_citations import TOPICS, official, citations_for_topic

class CleanupFailed(Exception):
    pass

def remote_program(topic):
    if topic not in TOPICS:
        raise ValueError("未対応の論点")
    # 案件ファイルやプロジェクト全体は読み込まない。
    source=Path(__file__).with_name("tavily_citations.py").read_text(encoding="utf-8")
    return source + "\nprint(json.dumps(citations_for_topic("+repr(topic)+"),ensure_ascii=False))\n"

API_URL="https://app.daytona.io/api"

class IoSandboxAdapter:
    def __init__(self,sandbox):
        self.raw=sandbox
    async def exec(self,*,argv,env,timeout,execution_timeout):
        # SDK 0.xのexecは文字列。公開コードだけを引用し、キーはenv引数で渡す。
        result=await self.raw.process.exec(shlex.join(argv),env=env,timeout=int(timeout))
        return SimpleNamespace(exit_code=result.exit_code,stdout=result.result)

class IoClientAdapter:
    def __init__(self):
        from daytona import AsyncDaytona, DaytonaConfig, CreateSandboxFromSnapshotParams
        configured=os.environ.get("DAYTONA_API_URL",API_URL).rstrip("/")
        if configured!=API_URL:
            raise ValueError("指定のAPI URLと異なります")
        self.params_type=CreateSandboxFromSnapshotParams
        self.raw=AsyncDaytona(DaytonaConfig(api_url=configured))
        self.v2=self  # 既存制御部の内部インターフェース。実際には0.x SDKを使用。
    async def __aenter__(self):
        await self.raw.__aenter__()
        return self
    async def __aexit__(self,*args):
        return await self.raw.__aexit__(*args)
    async def create(self,*,name,wait_seconds,create_timeout_seconds):
        params=self.params_type(name=name,labels={"hanron_run":name},language="python",public=False,ephemeral=True,auto_stop_interval=1,auto_delete_interval=0,ttl_minutes=3)
        return IoSandboxAdapter(await self.raw.create(params,timeout=wait_seconds))
    async def find_by_name(self,name):
        from daytona import ListSandboxesQuery
        return [IoSandboxAdapter(s) async for s in self.raw.list(ListSandboxesQuery(labels={"hanron_run":name}),request_timeout=5)]
    async def delete(self,sandbox):
        await self.raw.delete(sandbox.raw,timeout=8,wait=True)

async def _remote(topic, client_factory=None, budget=60):
    if client_factory is None:
        client_factory=IoClientAdapter
    name="hanron-citations-"+uuid.uuid4().hex
    cleanup={"status":"not_created"}
    async with client_factory() as client:
        sandbox=None
        async def run():
            nonlocal sandbox
            sandbox=await client.v2.create(name=name,wait_seconds=20,create_timeout_seconds=20)
            result=await sandbox.exec(argv=["python3","-c",remote_program(topic)],env={"TAVILY_API_KEY":os.environ["TAVILY_API_KEY"]},timeout=25,execution_timeout=25)
            if result.exit_code != 0:
                raise RuntimeError("リモート実行失敗")
            payload=json.loads(result.stdout)
            if not isinstance(payload,dict) or not isinstance(payload.get("citations"),list):
                raise ValueError("応答不正")
            if any(not isinstance(c,dict) or not official(c.get("url")) for c in payload["citations"]):
                raise ValueError("出典ドメイン不正")
            if payload.get("status") not in ("candidates","unknown","skipped"):
                raise ValueError("状態不正")
            return payload
        try:
            result=await asyncio.wait_for(run(),timeout=budget)
        finally:
            # 作成応答が失われた場合も、今回だけの一意名で探して削除する。
            async def cleanup_sandboxes():
                targets=[sandbox] if sandbox is not None else await client.v2.find_by_name(name)
                for target in targets:
                    await client.v2.delete(target)
                cleanup["status"]="delete_requested" if targets else "not_found"
            try:
                await asyncio.wait_for(cleanup_sandboxes(),timeout=10)
            except BaseException:
                cleanup["status"]="unconfirmed"
                # キーを含む例外は外へ出さない。利用者には残存の可能性を伝える。
                raise CleanupFailed(name) from None
        result.update(execution="daytona",cleanup=cleanup["status"])
        result["message"]="出典取得：Daytona sandbox で実行 ／ "+result.get("message","不明")
        return result

def collect_citations(topic="reasons", sandbox="local", local_fn=None, remote_fn=None):
    local=local_fn or citations_for_topic
    if sandbox != "daytona":
        result=local(topic);result.update(execution="local",cleanup="not_created")
        result["message"]="出典取得：手元のPC ／ "+result.get("message","不明")
        return result
    reason=""
    if not os.environ.get("DAYTONA_API_KEY"):
        reason="Daytonaキー未設定"
    elif not os.environ.get("TAVILY_API_KEY"):
        reason="Tavilyキー未設定"
    elif topic not in TOPICS:
        reason="未対応の論点"
    else:
        async def invoke():
            loop=asyncio.get_running_loop()
            task=asyncio.current_task()
            # Webの取消しが子プロセスに届いたとき、finallyの削除処理を通す。
            try:
                loop.add_signal_handler(signal.SIGTERM,task.cancel)
            except (NotImplementedError,RuntimeError,ValueError):
                pass
            try:
                return await (remote_fn or _remote)(topic)
            finally:
                try:loop.remove_signal_handler(signal.SIGTERM)
                except (NotImplementedError,RuntimeError,ValueError):pass
        try:
            return asyncio.run(invoke())
        except asyncio.CancelledError:
            raise KeyboardInterrupt from None
        except CleanupFailed as exc:
            reason="削除確認ができません。Daytona管理画面で環境名 "+str(exc)+" を確認してください"
        except Exception:
            reason="Daytona未導入・通信失敗・60秒タイムアウト等"
    result=local(topic)
    result.update(execution="local_fallback",fallback_reason=reason,cleanup="unconfirmed" if "削除確認" in reason else "see_remote_attempt")
    result["message"]="出典取得：手元のPCへ切替（"+reason+"） ／ "+result.get("message","不明")
    return result
