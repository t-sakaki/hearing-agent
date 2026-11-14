import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.tavily_citations import citations_for_topic, official
from src.rebuttal_pipeline import prepare
from src.approval import gate_from_stdin
from src.killswitch import request_stop
from io import StringIO

class PipelineTests(unittest.TestCase):
 def test_domains(self):
  self.assertTrue(official("https://www.courts.go.jp/a"))
  for u in ("https://courts.go.jp.evil.example/a","https://evilcourts.go.jp/a","http://courts.go.jp/a","https://x@courts.go.jp/a","https://courts.go.jp:8080/a",None):self.assertFalse(official(u))
 def test_missing_key(self):
  with patch.dict(os.environ,{"TAVILY_API_KEY":""}):
   self.assertEqual(citations_for_topic()["status"],"skipped")
 def test_search_failure(self):
  with patch.dict(os.environ,{"TAVILY_API_KEY":"test-only"}):
   r=citations_for_topic(post=lambda *a:(_ for _ in ()).throw(Exception("secret-value")))
  self.assertEqual(r["status"],"unknown");self.assertNotIn("secret-value",str(r))
 def test_extract_and_privacy(self):
  calls=[]
  def post(endpoint, payload):
   calls.append((endpoint,payload))
   if endpoint=="search":return {"results":[{"title":"公式", "url":"https://www.courts.go.jp/test", "content":"抜粋"},{"url":"https://courts.go.jp.evil.example/"}]}
   return {"results":[{"url":"https://www.courts.go.jp/test","raw_content":"本文"}],"failed_results":[]}
  with patch.dict(os.environ,{"TAVILY_API_KEY":"test-only"}):r=citations_for_topic("partial",post)
  self.assertEqual(len(r["citations"]),1);self.assertEqual(r["citations"][0]["excerpt"],"本文")
  self.assertFalse(calls[0][1]["include_answer"])
 def test_extract_failure_keeps_search(self):
  def post(endpoint,payload):
   if endpoint=="extract":raise TimeoutError()
   return {"results":[{"url":"https://soumu.go.jp/test","content":"検索抜粋"}]}
  with patch.dict(os.environ,{"TAVILY_API_KEY":"test-only"}):r=citations_for_topic(post=post)
  self.assertEqual(r["citations"][0]["snippet"],"検索抜粋");self.assertIn("失敗",r["message"])
 def test_order_and_no_private_search(self):
  events=[]
  def search(topic):events.append(topic);return {"citations":[],"message":"不明"}
  def complete(messages,**kwargs):
   events.append("llm");self.assertIn("private-marker",messages[1]["content"])
   return ('{"draft":"確認を求めます。","local_citations":["S1"],"unknowns":[]}',"test","mock",.01)
  with tempfile.TemporaryDirectory() as root:r=prepare("private-marker","[S1] 架空資料",root=root,search_fn=search,complete_fn=complete)
  self.assertEqual(events,["reasons","llm"]);self.assertEqual(r["status"],"draft")
 def test_no_sources_not_fabricated(self):
  with tempfile.TemporaryDirectory() as root:
   r=prepare("質問","",root=root,search_fn=lambda _: {"citations":[]})
  self.assertEqual(r["draft"],"");self.assertEqual(r["status"],"reference_only")
 def test_gate_and_stop(self):
  with tempfile.TemporaryDirectory() as root:
   self.assertEqual(gate_from_stdin("本文",StringIO("r\n"),root).decision,"reject")
   self.assertEqual(gate_from_stdin("本文",StringIO("a\n"),root).final_text,"本文")
   request_stop(root)
   self.assertEqual(gate_from_stdin("本文",StringIO("a\n"),root).decision,"killed")
   self.assertEqual(prepare("質問","資料",root=root)["status"],"stopped")

if __name__=="__main__":unittest.main()
