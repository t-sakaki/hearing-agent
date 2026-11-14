import fs from 'node:fs/promises';
import {Presentation,PresentationFile} from 'file:///C:/Program%20Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs';
const root='C:/Users/taira/hearing-agent';
const skill='C:/Users/taira/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const runtime='C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies';
await fs.mkdir(root+'/slides-build',{recursive:true});await fs.mkdir(root+'/slides',{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const navy='#193B49', teal='#256D70', muted='#526A75', bg='#F3F6F5';
function text(s,t,x,y,w,h,size=28,color=navy,bold=false){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={typeface:'Yu Gothic',fontSize:size,color,bold};return a;}
function slide(title,note=''){const s=p.slides.add();s.background.fill=bg;text(s,title,65,48,1150,80,42,navy,true);text(s,String(p.slides.items.length).padStart(2,'0'),1160,659,60,25,17,muted);s.speakerNotes.text=note;return s;}
function box(s,t,x,y,w=230,h=95){const a=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'#E0ECEA',line:{fill:'#9AB9B6',width:1}});text(s,t,x+16,y+20,w-32,h-25,25,navy,true);}
function line(s,x,y,w,h=2){s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:teal,line:{fill:'none',width:0}});}
let s=slide('陳述パートナー / Hanron Agent','約15秒。行政不服審査請求の現場で、相手の発言を聞き、手元の資料から根拠を探し、本人へ短い反論案を提示します。本発表は架空データです。');
text(s,'発言を聞き、資料を確かめ、\n本人の反論を支える',65,210,1130,190,57,navy,true);text(s,'口頭意見陳述のリアルタイム支援',70,435,1100,65,31,teal);text(s,'Agent Forge AI Hackathon   2026年11月14日\n技術構想と現在のプロトタイプ / デモ資料はすべて架空',70,570,1100,70,22,muted);
s=slide('その場で根拠を探す負担','約20秒。主な課題は、その場の発言を聞きながら、自分の資料を探し、短く答える同時作業です。特定の事件情報は示しません。');
text(s,'相手の説明は、その場で進む',70,180,1120,65,39,navy,true);text(s,'聞き取りながら資料を探すと、反論の機会を逃しやすい。',70,280,1120,70,29,muted);text(s,'必要な支援',70,405,350,50,25,teal,true);text(s,'短い反論案と、その根拠を同じ画面へ。\n案件のMarkdownを差し替えて、他の事案でも使う。',70,475,1130,120,33,navy);
s=slide('リアルタイム処理の全体構造','約30秒。ここは完成後の接続設計です。既存Pythonに音声処理がありますが、新Web画面への接続は未完了です。入力資料は概要・時系列・争点・双方の主張・根拠資料・未確認事項。');
box(s,'マイク音声',65,190,230);line(s,295,237,65);box(s,'逐次文字起こし',360,190,270);line(s,630,237,65);box(s,'発言の確定・訂正',695,190,330);
line(s,850,285,2,50);box(s,'司令役 / 発言ID・改訂管理',360,335,665);box(s,'案件別の資料\nMarkdown\n事前に索引化',65,335,230,125);line(s,295,382,65);line(s,690,430,2,50);box(s,'資料検索・争点分類・反論生成',360,480,665);text(s,'出力：本人用の短文 ＋ 資料名・見出し・原文抜粋',70,610,1120,45,27,teal,true);
s=slide('オーケストレーションの制御','約30秒。AgentFieldによる接続を計画しています。現時点の制御部は依存なしJavaScriptです。並列実行、出典IDの検証、根拠なし分岐、STOP時の古い結果棄却を単体確認しました。出典IDの検証は内容の正しさを保証するものではありません。\n参考：https://www.agentfield.ai/docs/agentfield/build/coordination/orchestration');
box(s,'確定した発言',65,180,230);line(s,295,225,40);line(s,335,200,2,132);line(s,335,200,30);line(s,335,330,30);box(s,'資料検索',365,150,235);box(s,'争点分類',365,285,235);line(s,600,200,35);line(s,600,330,35);line(s,635,200,2,132);line(s,635,255,35);box(s,'統合・反論生成',670,210,270);line(s,940,255,40);box(s,'出典ID確認',980,210,235);text(s,'資料検索と争点分類を並行実行',70,430,1120,50,31,teal,true);text(s,'改訂された発言の古い結果は棄却。STOPで取消。\n根拠がなければ「不明」と確認質問を提示。\nTavilyの追加調査は別経路で進め、反論を待たせない。',70,500,1130,140,27);
s=slide('即時表示と劇場モード','約25秒。本番の即時表示は反論案と出典を優先。劇場モードは一つのAIによる架空の3役です。実在の学者や複数の賛同者を装いません。現状は定型台本で、端末の日本語合成音声を使います。');
text(s,'本番の即時表示',70,180,500,55,34,teal,true);text(s,'相手発言を左へ\n反論案を中央へ大きく\n引用原文を右へ',70,265,500,160,31);text(s,'デモの劇場モード',680,180,520,55,34,teal,true);text(s,'分析役：主張を整理\n市民の視点：疑問を言葉に\n学術的な検討役：根拠を確認',680,265,520,170,29);text(s,'3役は順番に発声。声は選択式。停止操作を常時表示。\n本人用の反論案と出典は、音声を待たずに表示する。',70,535,1120,100,28,navy,true);
s=slide('技術スタックと提供技術','約30秒。TavilyはAPI接続コードとサンプル切替を実装済みですが、実APIの疎通は未確認です。AgentFieldはオーケストレーションの接続予定。DaytonaとNosanaは追加候補で、現在は未接続です。\n出典：https://luma.com/Tokyoagentforge\nhttps://help.tavily.com/articles/4840311948-tavily-search-api\nhttps://www.agentfield.ai/docs/agentfield/reference/sdks/python');
text(s,'実装済みの土台',70,170,500,50,31,teal,true);text(s,'Web：HTML / CSS / JavaScript\nサーバー：Node.js標準HTTP\n音声：既存Python STT + ブラウザーTTS\n制御：並列処理・改訂管理・出典ID確認',70,245,1130,190,27);text(s,'提供技術の接続方針',70,465,500,50,31,teal,true);text(s,'Tavily：出典検索コードあり、実通信は未確認\nAgentField：処理連携と実行履歴を接続予定\nDaytona / Nosana：検証環境・推論の追加候補',70,535,1130,110,25);
s=slide('完成までの優先順位と検証','約25秒。発言終了から最初の根拠付き反論まで1〜2秒を目標としますが、実測値ではありません。完成後はSTT・検索・生成を分けて時間を記録します。現時点でAIによる即時反論まで動くとは主張しません。');
text(s,'1〜2秒',70,175,480,115,78,teal,true);text(s,'発言終了から最初の候補までの目標\n未計測・達成保証なし',75,310,520,90,26,muted);text(s,'今日の実装順',680,180,500,50,33,navy,true);text(s,'音声と資料検索の接続\n根拠付き生成と取消制御\n提供技術の実呼出し\n遅延計測とデモの通し確認',680,265,510,210,29);text(s,'現在：Web画面・3役台本・制御部の単体確認まで\n未完了：音声認識と生成のWeb接続、AgentField連携',70,540,1120,90,26,navy,true);
await (await PresentationFile.exportPptx(p)).save(root+'/slides-build/candidate.pptx');
for(let i=0;i<p.slides.items.length;i++){const b=await p.export({slide:p.slides.items[i],format:'png',scale:0.8});await fs.writeFile(root+'/slides-build/slide-'+(i+1)+'.png',new Uint8Array(await b.arrayBuffer()));}
const {finalizePresentation}=await import('file:///'+skill+'/container_tools/artifact_tool_utils.mjs');
const result=await finalizePresentation({workspaceDir:root,candidatePath:root+'/slides-build/candidate.pptx',finalPath:root+'/slides/hanron-agent-hackathon.pptx',pythonExecutable:runtime+'/python/python.exe',integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],fontPolicy:{basis:'design',families:['Yu Gothic']},verifyArtifactToolImport:true,receiptPath:root+'/slides-build/validation.json'});console.log(JSON.stringify(result));
