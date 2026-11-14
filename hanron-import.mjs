// ブリーフ本文はブラウザーのメモリーだけで扱う。保存・送信しない。
function plain(s){return s.replace(/\*\*/g,'').replace(/^[-*] /gm,'').trim();}
function section(md,n){return md.match(new RegExp('^## '+n+'[.．][^\\n]*\\n([\\s\\S]*?)(?=^## |$(?![\\s\\S]))','m'))?.[1]||'';}
export function parseBrief(md,name='案件資料.md'){
 const table=section(md,1);const rows=table.split('\n').filter(l=>l.startsWith('|')).map(l=>l.split('|').slice(1,-1).map(plain));
 const agency=rows.find(r=>r[0]==='処分庁')?.[1]||'読み込んだ案件';
 const disposition=rows.find(r=>r[0]==='対象の処分')?.[1]||'口頭意見陳述の準備';
 const timeline=section(md,2).split('\n').filter(l=>l.startsWith('|')).map(l=>l.split('|').slice(1,-1).map(plain)).filter(r=>r.length>=3&&r[0]!=='日付'&&!/^[-: ]+$/.test(r[0])).map((r,i)=>({date:r[0],text:r[1],source:'T'+(i+1)}));
 const qa=section(md,6);const blocks=qa.split(/(?=^### Q\d+)/m).filter(b=>/^### Q\d+/.test(b));
 const issues=[],sources=timeline.map(t=>({id:t.source,title:name+' 第2節 '+t.date,content:t.text,local:true}));
 for(const block of blocks){const q=block.match(/^### (Q\d+)\s*(.*)/);const answer=block.match(/^- \*\*たたき台\*\*[：:]([^\n]+)/m);if(!q||!answer)continue;const id=q[1],text=plain(answer[1]);const field=label=>plain(block.match(new RegExp('^- \\*\\*'+label+'\\*\\*[：:]([^\\n]+)','m'))?.[1]||'');const source='B'+id;const concepts=['存否','部分開示','本人','理由','探索','制度','確認','不明'].filter(t=>text.includes(t));const topic=/部分開示|第8条/.test(block)?'partial':/存否|第10条/.test(block)?'existence':'reasons';
 issues.push({id,shortAnswer:field('短答'),detailAnswer:field('詳答'),keywords:field('検出語'),sourceNotes:field('根拠'),caution:field('注意'),title:q[2],claim:text,agency:'相手の実際の発言ではなく、資料に記載した想定質問です。',question:q[2],answer:text,source,feedbackSource:source,topic,unknown:'ブリーフの回答案はたたき台です。原資料と未確認事項を確認してください。',followup:'この回答の根拠箇所と、まだ確認できていない点を挙げてください。',rubric:[{id:'concept',label:'資料にある論点の語句に触れる',terms:concepts.length?concepts:['確認']},{id:'qualification',label:'根拠や未確認事項を留保する',terms:['資料','根拠','確認','不明','断定しない','考えます']}]});sources.push({id:source,title:name+' 第6節 '+id+'（原資料未照合）',content:plain(block),local:true});}
 if(!issues.length)throw Error('第6節のQ番号と「たたき台」を含むブリーフを選択してください。');
 return {isLocal:true,title:agency+' ／ 実案件資料',summary:disposition+'。読込資料：'+name+'。内容は原資料と照合してください。',timeline,issues,sources};
}

// 実案件の台本はブラウザー内で構成し、生成APIには渡さない。
export function buildLocalTheater(caseData,issue){
 if(!caseData?.isLocal||!issue?.question||!issue?.answer)throw Error('想定問答を読み込んでください。');
 const short=issue.shortAnswer||issue.answer,detail=issue.detailAnswer||issue.answer;
 const remarks=[['office','市側の想定反論です。'+issue.question],['male','ええっ！？それで納得しろということ！？どの資料で確かめられるの！'],['female','ほんと、それ！もう、もどかしい！この件に即して、分かる言葉で説明して！'],['assistant',short],['office','この説明に対する請求人側の見解と、その根拠を確認します。'],['male','そう、そこ！一般論だけでなく、この件のどこに当てはまるのか聞きたい！'],['female','そうよ！補佐AIさん、資料と、まだ分からないことを分けて！'],['assistant',detail]];
 return remarks.map(([role,text],n)=>({type:'message',id:'L'+(n+1),role,language:'ja',text,ja:text,en:'Local case material: English translation has not been verified.',depth:n<3?0:n===7?2:1,mode:role==='office'?'市の実発言ではない想定 / Hypothetical':'手元の想定問答 / Local prepared script',citations:role==='assistant'?[{id:issue.feedbackSource,title:'手元資料 '+issue.id,content:(issue.sourceNotes||'原資料との照合が必要')+' 留保：'+(issue.caution||issue.unknown)}]:[]}));
}
