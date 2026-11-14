// 架空の反論書にある確認項目を照合する。法的な自動採点ではない。
export function evaluateAnswer(issue,answer){
 const text=answer.trim().normalize('NFKC');
 const matched=issue.rubric.filter(r=>r.terms.some(term=>text.includes(term)));
 const missing=issue.rubric.filter(r=>!matched.some(m=>m.id===r.id));
 const warnings=[];
 if(/必ず(?!しも)|絶対|違法(?:です|である|と確定)|確実に勝/.test(text))warnings.push('強い断定があります。資料で確認できる主張の範囲に言い換えてください。');
 if((issue.id==='I2'||issue.topic==='partial')&&/分離(?:は|が)?(?:可能です|できます|できることを確認|可能と確認)|分離できると断定/.test(text))warnings.push('分離可能性は未確認です。できると断定せず、様式の確認を求めてください。');
 return {matched:matched.map(r=>r.label),missing:missing.map(r=>r.label),warnings,example:issue.answer,claim:issue.claim,source:issue.feedbackSource,followup:issue.followup,points:matched.length,maximum:issue.rubric.length};
}
export function sourceFallback(c,issue,message='サンプル出典（検索未実施）'){
 return {mode:c.isLocal?'local':'sample',message:c.isLocal?message.replaceAll('サンプル出典','手元資料'):message,results:c.sources.filter(s=>[issue.source,issue.feedbackSource].includes(s.id)).map(s=>({title:s.title+' ['+s.id+']',content:s.content,url:'',sourceId:s.id})),fetchedAt:null};
}
export function officialUrl(url){try{const u=new URL(url);return u.protocol==='https:'&&!u.username&&!u.password&&(!u.port||u.port==='443')&&(['go.jp','lg.jp'].some(d=>u.hostname.endsWith('.'+d))||['city.anjo.aichi.jp','pref.aichi.jp'].some(d=>u.hostname===d||u.hostname.endsWith('.'+d)));}catch{return false;}}
export async function searchSources(c,issue,{offline=false,key='',fetcher=fetch,jurisdiction='general',signal}={}){
 if(offline||!key)return sourceFallback(c,issue,offline?'オフライン実演：サンプル出典':'キー未設定：サンプル出典');
 const locality=jurisdiction==='anjo'?'安城市情報公開条例 ':jurisdiction==='aichi'?'愛知県情報公開条例 ':'';
 const query=locality+(issue.topic==='existence'?'情報公開 存否応答拒否 要件 答申 裁決 条例':issue.topic==='partial'?'情報公開 部分開示 分離可能性 答申 裁決 条例':'情報公開 不開示決定 理由提示 答申 裁決 条例');
 try{const r=await fetcher('https://api.tavily.com/search',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+key},body:JSON.stringify({query,search_depth:'basic',max_results:4,include_domains:['fufukudb.search.soumu.go.jp','go.jp','lg.jp','city.anjo.aichi.jp','pref.aichi.jp'],include_domains_mode:'restrict',include_answer:false}),signal:signal?AbortSignal.any([signal,AbortSignal.timeout(8000)]):AbortSignal.timeout(8000)});if(!r.ok)throw Error();const data=await r.json();if(!Array.isArray(data.results))throw Error();const results=data.results.filter(x=>officialUrl(x.url)&&typeof x.content==='string'&&x.content.trim()).filter(x=>{const u=new URL(x.url);return !(u.hostname==='fufukudb.search.soumu.go.jp'&&/^\/koukai\/(Main)?\/?$/.test(u.pathname));}).map(x=>({title:String(x.title||'公式資料'),url:x.url,content:x.content.slice(0,700)})).sort((a,b)=>Number(new URL(b.url).hostname==='fufukudb.search.soumu.go.jp')-Number(new URL(a.url).hostname==='fufukudb.search.soumu.go.jp'));if(!results.length)return sourceFallback(c,issue,'公式出典を取得できませんでした：サンプル出典');return {mode:'live',message:'Tavily検索結果（抜粋・主張との一致は要確認）',results,fetchedAt:new Date().toISOString()};}catch{return sourceFallback(c,issue,'検索通信に失敗しました：サンプル出典で継続');}
}
