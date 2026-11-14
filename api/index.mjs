import {createServer} from '../hanron-server.mjs';
const server=createServer({theater:true});
const handle=server.listeners('request')[0];
export default function handler(req,res){
 const url=new URL(req.url,'https://localhost');
 const path=url.searchParams.get('__path');
 if(path!==null){url.searchParams.delete('__path');req.url='/'+path+(url.search?'?'+url.searchParams.toString():'');}
 if(/^\/api\/hearing\/(warm|stt|stop)$/.test(new URL(req.url,'https://localhost').pathname)){res.writeHead(503,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'ローカルfaster-whisperはPC版で利用してください。公開版は文字入力で継続できます。'}));return;}
 if(req.body!==undefined){const body=typeof req.body==='string'?req.body:JSON.stringify(req.body);req[Symbol.asyncIterator]=async function*(){yield Buffer.from(body);};}
 return handle(req,res);
}
