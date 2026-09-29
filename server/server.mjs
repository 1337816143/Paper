import http from 'node:http';
import {pathToFileURL} from 'node:url';
import {initialize,report,REPOSITORY,DATA_BRANCH,readData,writeData,verifyPrivate,branchInfo,problem} from './github-vault.mjs';
import {authenticate,exchange,renew,revoke,createInvite,newSession,trustedWorkflow} from './device-auth.mjs';
export const VERSION='5.2.0';
const ORIGIN='https://1337816143.github.io';const counters=new Map();
async function readJSON(req){let length=0;const chunks=[];for await(const chunk of req){length+=chunk.length;if(length>1700000)throw problem(413,'请求过大。');chunks.push(chunk);}try{return chunks.length?JSON.parse(Buffer.concat(chunks)):{};}catch{throw problem(400,'请求必须为JSON。');}}
function rate(req,path){const ip=String(req.headers['x-forwarded-for']||req.socket.remoteAddress).split(',')[0].trim(),id=ip+'|'+(path==='/auth/exchange'?'exchange':'normal');let row=counters.get(id);if(!row||row.until<Date.now())row={until:Date.now()+600000,count:0};row.count++;counters.set(id,row);if(row.count>(path==='/auth/exchange'?30:4000))throw problem(429,'请稍后重试；本机数据保留。');if(counters.size>10000)for(const [k,v]of counters)if(v.until<Date.now())counters.delete(k);}
async function route(req,path,body){
 if(path==='/healthz')return {version:VERSION,ready:report.ready,plan:'free',storage:'private GitHub data branch',publicDataAccess:false};
 if(!report.ready)throw problem(503,'免费后台正在唤醒或验证授权，请稍候；本机笔记保留。');
 if(path.startsWith('/admin/')){
  const identity=await trustedWorkflow(req.headers.authorization);
  if(path==='/admin/status')return {...report,version:VERSION,note:'Endpoint capabilities verified independently; fine-grained token grants cannot be fully enumerated from repository permissions.'};
  if(path==='/admin/invite')return createInvite(DATA_BRANCH,'个人首台设备',604800);
  if(path==='/admin/test-session')return newSession('paper-user-data-test-'+identity.run_id,'Synthetic acceptance test');
  throw problem(404,'Not found');
 }
 if(path==='/auth/exchange')return exchange(body.grant,body.label);
 const user=await authenticate(req.headers.authorization);
 if(path==='/auth/status')return {connected:true,version:VERSION,deviceId:user.id,expiresAt:user.exp,configuration:{repository:REPOSITORY,branch:user.branch}};
 if(path==='/auth/renew')return renew(user);
 if(path==='/auth/invite')return createInvite(user.branch,body.label||'另一台个人设备');
 if(path==='/auth/revoke')return revoke(user);
 if(body.branch&&body.branch!==user.branch)throw problem(403,'设备不允许切换到其他数据分支。');
 if(path==='/v1/repository')return verifyPrivate();
 if(path==='/v1/branch'){await verifyPrivate();return branchInfo(user.branch);}
 if(path==='/v1/read'){await verifyPrivate();return readData(body.path,user.branch,false);}
 if(path==='/v1/write')return writeData(body.path,body.content,body.sha,user.branch);
 throw problem(404,'Not found');
}
export function createServer(){return http.createServer(async(req,res)=>{
 const origin=req.headers.origin;res.setHeader('Cache-Control','no-store, max-age=0');res.setHeader('X-Content-Type-Options','nosniff');res.setHeader('Referrer-Policy','no-referrer');res.setHeader('X-Robots-Tag','noindex, nofollow');res.setHeader('Vary','Origin');
 if(origin===ORIGIN){res.setHeader('Access-Control-Allow-Origin',ORIGIN);res.setHeader('Access-Control-Allow-Headers','Content-Type, Authorization');res.setHeader('Access-Control-Allow-Methods','GET, POST, OPTIONS');res.setHeader('Access-Control-Max-Age','600');}
 try{
  if(origin&&origin!==ORIGIN)throw problem(403,'不允许的网页来源。');
  if(req.method==='OPTIONS'){res.writeHead(204);res.end();return;}
  const url=new URL(req.url,'http://local');if(url.search)throw problem(400,'请勿把授权放入URL。');
  if(url.pathname==='/robots.txt'){res.writeHead(200,{'Content-Type':'text/plain'});res.end('User-agent: *\nDisallow: /\n');return;}
  if(req.method==='GET'&&url.pathname==='/'){res.writeHead(200,{'Content-Type':'text/plain; charset=utf-8'});res.end('Paper Lab private synchronization service v'+VERSION+'\nFree Render instance. Read at https://1337816143.github.io/Paper/\nPrivate data requires device authorization.');return;}
  if(!['GET','POST'].includes(req.method)||req.method==='GET'&&url.pathname!=='/healthz')throw problem(405,'请使用受保护的JSON接口。');
  if(req.method==='POST'&&!/^application\/json(?:;|$)/i.test(req.headers['content-type']||''))throw problem(415,'需要application/json。');
  rate(req,url.pathname);const value=await route(req,url.pathname,req.method==='POST'?await readJSON(req):{});
  res.writeHead(200,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify(value));
 }catch(e){const status=Number.isInteger(e.status)&&e.status>=400&&e.status<=599?e.status:503;res.writeHead(status,{'Content-Type':'application/json; charset=utf-8'});res.end(JSON.stringify({error:Number.isInteger(e.status)?e.message:'后台暂时无法连接；本机数据保留，稍后自动重试。',retryable:[429,500,502,503,504].includes(status)}));}
});}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){createServer().listen(Number(process.env.PORT||10000),'0.0.0.0',()=>console.log(JSON.stringify({event:'server-listening',version:VERSION,plan:'free'})));let initializing=false;const start=async()=>{if(initializing)return;initializing=true;try{await initialize();}catch{console.log(JSON.stringify({event:'initialization-failed',ready:false}));}finally{initializing=false;}};start();setInterval(()=>{if(!report.ready)start();},600000).unref();}
