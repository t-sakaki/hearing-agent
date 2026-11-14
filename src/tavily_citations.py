"""公開論点だけを送るTavily Search/Extract。例外やキーは出力しない。"""
import json
import os
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DOMAINS = ("courts.go.jp", "laws.e-gov.go.jp", "e-gov.go.jp", "soumu.go.jp", "city.anjo.aichi.jp")
TOPICS = {"reasons": "情報公開 不開示決定 理由提示", "partial": "情報公開 部分開示 分離可能性", "existence": "情報公開 存否応答拒否 要件"}

def official(url):
    try:
        p = urlparse(url)
        return p.scheme == "https" and not p.username and not p.password and p.port in (None, 443) and any(p.hostname == d or p.hostname.endswith("." + d) for d in DOMAINS)
    except (ValueError, TypeError, AttributeError):
        return False

def _post(endpoint, payload):
    key = os.environ.get("TAVILY_API_KEY", "")
    req = Request("https://api.tavily.com/" + endpoint, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", "Authorization": "Bearer " + key}, method="POST")
    with urlopen(req, timeout=8) as response:
        return json.load(response)

def citations_for_topic(topic="reasons", post=None):
    query = TOPICS.get(topic)
    if query is None:
        return {"status": "unknown", "message": "不明（未対応の論点）", "citations": []}
    if not os.environ.get("TAVILY_API_KEY"):
        return {"status": "skipped", "message": "不明（Tavilyキー未設定）", "citations": []}
    call = post or _post
    try:
        data = call("search", {"query": query, "search_depth": "basic", "max_results": 3, "include_domains": list(DOMAINS), "include_domains_mode": "restrict", "include_answer": False, "include_raw_content": False})
        found=[]
        for x in data.get("results", []):
            if isinstance(x, dict) and official(x.get("url")) and not any(c["url"] == x["url"] for c in found):
                found.append({"id": "W"+str(len(found)+1), "title": str(x.get("title") or "公式資料"), "url": x["url"], "snippet": str(x.get("content") or "")[:1200], "excerpt": "", "verified": False})
        found=found[:3]
        if not found:
            return {"status": "unknown", "message": "不明（公式出典が見つかりません）", "citations": []}
        extract_failed=False
        try:
            extracted=call("extract", {"urls": [x["url"] for x in found[:2]], "extract_depth": "basic", "format": "markdown", "query": query, "chunks_per_source": 2})
            extract_failed=bool(extracted.get("failed_results"))
            for x in extracted.get("results", []):
                for c in found:
                    if c["url"] == x.get("url"):
                        c["excerpt"] = str(x.get("raw_content") or "")[:1800]
        except Exception:
            extract_failed=True
        return {"status": "candidates", "message": "公式出典候補（主張との一致は本人確認）" + ("／本文抽出は一部または全部失敗" if extract_failed else ""), "query": query, "citations": found}
    except Exception:
        return {"status": "unknown", "message": "不明（検索通信失敗）", "citations": []}
