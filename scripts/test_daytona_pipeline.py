import asyncio
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.daytona_citations import _remote, collect_citations, remote_program, CleanupFailed

class FakeClient:
 def __init__(self,mode="ok"):
  self.mode=mode;self.v2=self;self.calls=[];self.sandbox=SimpleNamespace(exec=self.exec)
 async def __aenter__(self):return self
 async def __aexit__(self,*args):self.calls.append(("close",{}))
 async def create(self,**kw):
  self.calls.append(("create",kw))
  if self.mode=="create_fail":raise TimeoutError()
  return self.sandbox
 async def find_by_name(self,name):self.calls.append(("find",name));return [self.sandbox]
 async def delete(self,target):
  self.calls.append(("delete",target))
  if self.mode=="delete_fail":raise TimeoutError()
 async def exec(self,**kw):
  self.calls.append(("exec",kw))
  if self.mode=="exec_fail":raise RuntimeError("not-logged")
  if self.mode=="hang":await asyncio.sleep(10)
  if self.mode=="invalid":return SimpleNamespace(exit_code=0,stdout='invalid')
  url="https://evil.example/" if self.mode=="bad_domain" else "https://www.courts.go.jp/test"
  return SimpleNamespace(exit_code=0,stdout=json.dumps({"status":"candidates","message":"候補","citations":[{"id":"W1","title":"公式","url":url,"snippet":"抜粋","excerpt":""}]}))

class DaytonaTests(unittest.TestCase):
 def test_success_and_payload(self):
  f=FakeClient()
  with patch.dict(os.environ,{"TAVILY_API_KEY":"test-only","DAYTONA_API_KEY":"daytona-test","NOUS_API_KEY":"must-not-send"}):r=asyncio.run(_remote("partial",lambda:f))
  self.assertEqual(r["execution"],"daytona");self.assertEqual(r["cleanup"],"delete_requested")
  sent=next(c[1] for c in f.calls if c[0]=="exec")
  self.assertEqual(sent["env"],{"TAVILY_API_KEY":"test-only"});self.assertNotIn("test-only",str(sent["argv"]))
  self.assertEqual([c[0] for c in f.calls],['create','exec','delete','close'])
  self.assertNotIn('volumes',f.calls[0][1])
 def test_failures_delete(self):
  for mode in ('exec_fail','invalid','bad_domain'):
   f=FakeClient(mode)
   with self.subTest(mode=mode),patch.dict(os.environ,{"TAVILY_API_KEY":"test-only"}):
    with self.assertRaises(Exception):asyncio.run(_remote("reasons",lambda:f))
    self.assertIn('delete',[c[0] for c in f.calls])
 def test_create_failure_recovers_by_unique_name(self):
  f=FakeClient('create_fail')
  with self.assertRaises(TimeoutError):asyncio.run(_remote('reasons',lambda:f))
  self.assertEqual([c[0] for c in f.calls],['create','find','delete','close'])
 def test_timeout_deletes(self):
  f=FakeClient('hang')
  with patch.dict(os.environ,{"TAVILY_API_KEY":"test-only"}):
   with self.assertRaises(TimeoutError):asyncio.run(_remote('partial',lambda:f,budget=.01))
  self.assertIn('delete',[c[0] for c in f.calls])
 def test_missing_key_fallback(self):
  with patch.dict(os.environ,{"DAYTONA_API_KEY":""}):r=collect_citations('partial','daytona',local_fn=lambda _: {"status":"unknown","message":"不明","citations":[]})
  self.assertEqual(r['execution'],'local_fallback')
 def test_remote_failure_fallback(self):
  async def fail(topic):raise RuntimeError('secret-not-output')
  with patch.dict(os.environ,{"DAYTONA_API_KEY":"test-only","TAVILY_API_KEY":"test-only"}):r=collect_citations('reasons','daytona',local_fn=lambda _: {"status":"unknown","message":"不明","citations":[]},remote_fn=fail)
  self.assertEqual(r['execution'],'local_fallback');self.assertNotIn('secret-not-output',str(r))
 def test_cleanup_failure_visible(self):
  async def fail(topic):raise CleanupFailed('hanron-citations-test')
  with patch.dict(os.environ,{"DAYTONA_API_KEY":"test-only","TAVILY_API_KEY":"test-only"}):r=collect_citations('reasons','daytona',local_fn=lambda _: {"status":"unknown","message":"不明","citations":[]},remote_fn=fail)
  self.assertEqual(r['cleanup'],'unconfirmed');self.assertIn('hanron-citations-test',r['message'])
 def test_delete_error_not_hidden(self):
  f=FakeClient('delete_fail')
  with patch.dict(os.environ,{"TAVILY_API_KEY":"test-only"}):
   with self.assertRaises(CleanupFailed):asyncio.run(_remote('partial',lambda:f))
 def test_remote_code_only(self):
  code=remote_program('partial')
  self.assertNotIn('hantai-agent-brief',code);self.assertNotIn('read_text',code);self.assertNotIn('DAYTONA_API_KEY',code)
  with self.assertRaises(ValueError):remote_program('private material')
if __name__=='__main__':unittest.main()
