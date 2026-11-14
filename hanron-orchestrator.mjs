// 依存なしの制御部。各処理は接続先から注入する。AgentField接続は別途必要。
export function createOrchestrator({retrieve,classify,generate,onEvent=()=>{}}){
 let revision=0,controller;
 const stop=()=>{revision++;controller?.abort();onEvent({stage:'stopped',revision});};
 return {stop,async run({utteranceId,text}){
 controller?.abort();const own=++revision;controller=new AbortController();const signal=controller.signal;
 const context={utteranceId,revision:own,signal};const started=performance.now();
 const current=()=>own===revision&&!signal.aborted;
 const emit=(stage,extra={})=>{if(current())onEvent({utteranceId,revision:own,stage,elapsedMs:performance.now()-started,...extra});};
 const step=async(name,fn)=>{emit(name+':running');const result=await fn();emit(name+':done');return result;};
 try{
 emit('started');
 const [sources,issue]=await Promise.all([step('retrieve',()=>retrieve(text,context)),step('classify',()=>classify(text,context))]);
 if(!current())return null;
 if(!sources.length){const result={kind:'clarify',text:'根拠資料が見つかりません。発言の趣旨と対象資料を確認してください。',citations:[]};emit('ready',{result});return result;}
 const result=await step('generate',()=>generate({text,sources,issue},context));
 if(!current())return null;
 const ids=new Set(sources.map(s=>s.id));
 if(!Array.isArray(result.citations)||!result.citations.length||result.citations.some(id=>!ids.has(id)))throw new Error('INVALID_CITATIONS');
 emit('ready',{result});return result;
 }catch(error){if(!current())return null;emit('error',{reason:error.message==='INVALID_CITATIONS'?'出典を確認できません':'処理に失敗しました'});return null;}
 }};
}
