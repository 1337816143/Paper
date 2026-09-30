import {createServer} from 'node:http';
import {createCipheriv,createDecipheriv,createHash,randomBytes,timingSafeEqual} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {createReadStream} from 'node:fs';
import {realpath,stat} from 'node:fs/promises';
import {resolve,sep} from 'node:path';

const REPOSITORY='1337816143/My-Evolution';
const COOKIE='__Host-paper-oauth';
const GITHUB_AUTHORIZE='https://github.com/login/oauth/authorize';
const GITHUB_TOKEN='https://github.com/login/oauth/access_token';
const GITHUB_API='https://api.github.com';
const TOKEN=/^gh[opusr]_[A-Za-z0-9_.-]{16,4096}$/;
const REFRESH=/^ghr_[A-Za-z0-9_.-]{16,4096}$/;
const b64=value=>Buffer.from(value).toString('base64url');
const json=(res,status,body,headers={})=>{res.writeHead(status,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff',...headers});res.end(JSON.stringify(body));};
const fixed=(a,b)=>{const x=Buffer.from(String(a)),y=Buffer.from(String(b));return x.length===y.length&&timingSafeEqual(x,y);};
const plainError=(res,status,message)=>json(res,status,{error:message});

export function checkedConfig(env=process.env){
  const clientId=env.GITHUB_APP_CLIENT_ID,clientSecret=env.GITHUB_APP_CLIENT_SECRET;
  const baseUrl=env.PUBLIC_BASE_URL,siteOrigin=env.PAPER_SITE_ORIGIN;
  const cookieKey=Buffer.from(env.COOKIE_KEY_BASE64URL||'','base64url');
  if(!clientId||!clientSecret||cookieKey.length!==32)throw Error('Gateway credentials are not configured');
  for(const [label,url] of [['PUBLIC_BASE_URL',baseUrl],['PAPER_SITE_ORIGIN',siteOrigin]]){
    let parsed;try{parsed=new URL(url);}catch{throw Error(label+' is invalid');}
    if(parsed.origin!==url||parsed.username||parsed.password||parsed.protocol!=='https:'&&!(env.ALLOW_INSECURE_LOCAL==='1'&&parsed.hostname==='127.0.0.1'))throw Error(label+' must be an allowed origin');
  }
  if(siteOrigin!==baseUrl||new URL(siteOrigin).hostname.endsWith('.github.io'))throw Error('A dedicated same-origin Paper host is required');
  return {clientId,clientSecret,baseUrl,siteOrigin,cookieKey,siteDir:env.PAPER_SITE_DIR?resolve(env.PAPER_SITE_DIR):null,expectedLogin:'1337816143',repository:REPOSITORY};
}

function seal(data,key){const iv=randomBytes(12),cipher=createCipheriv('aes-256-gcm',key,iv);const body=Buffer.concat([cipher.update(JSON.stringify(data),'utf8'),cipher.final()]);return [b64(iv),b64(cipher.getAuthTag()),b64(body)].join('.');}
function unseal(token,key){const parts=String(token||'').split('.');if(parts.length!==3||parts.some(p=>p.length>1200))throw Error('Invalid OAuth state');const [iv,tag,body]=parts.map(p=>Buffer.from(p,'base64url'));if(iv.length!==12||tag.length!==16)throw Error('Invalid OAuth state');const decipher=createDecipheriv('aes-256-gcm',key,iv);decipher.setAuthTag(tag);return JSON.parse(Buffer.concat([decipher.update(body),decipher.final()]).toString('utf8'));}
function cookieValue(req){const match=(req.headers.cookie||'').match(/(?:^|;\s*)__Host-paper-oauth=([^;]+)/);return match?.[1]||'';}
const cookieHeader=value=>`${COOKIE}=${value}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=600`;
const clearCookie=`${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0`;
const safeHeaders={'Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY'};
const MIME={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.pdf':'application/pdf','.woff2':'font/woff2','.wasm':'application/wasm','.zip':'application/zip','.webmanifest':'application/manifest+json'};
const SITE_CSP="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; font-src 'self' data:; connect-src 'self' https:; worker-src 'self' blob:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'";

async function serveSite(req,res,root,pathname){
  if(!root||!['GET','HEAD'].includes(req.method))return plainError(res,404,'Not found');
  let segments;try{segments=(pathname==='/'?'/index.html':pathname).slice(1).split('/').map(decodeURIComponent);}catch{return plainError(res,400,'Invalid path');}
  if(segments.some(s=>!s||s==='.'||s==='..'||s.startsWith('.')||s.includes('\\')||s.includes('/')||s.includes('\0')))return plainError(res,404,'Not found');
  const target=resolve(root,...segments);
  if(!target.startsWith(root+sep))return plainError(res,404,'Not found');
  try{
    const actual=await realpath(target),info=await stat(actual);
    if(!actual.startsWith(root+sep)||!info.isFile())return plainError(res,404,'Not found');
    const extension='.'+segments.at(-1).split('.').at(-1).toLowerCase();
    const headers={...safeHeaders,'Content-Type':MIME[extension]||'application/octet-stream','Content-Length':String(info.size),'Cache-Control':'no-cache'};
    if(extension==='.html')headers['Content-Security-Policy']=SITE_CSP;
    if(pathname==='/downloads/Paper-Lab-offline.html')headers['Content-Disposition']='attachment; filename="Paper-Lab-offline.html"';
    res.writeHead(200,headers);if(req.method==='HEAD')return res.end();
    createReadStream(actual).on('error',()=>res.destroy()).pipe(res);return;
  }catch{return plainError(res,404,'Not found');}
}

async function githubJson(fetchImpl,url,options){const response=await fetchImpl(url,{...options,signal:AbortSignal.timeout(12000)});if(!response.ok)throw Error('GitHub request failed');const data=await response.json();if(data.error||!data||typeof data!=='object')throw Error('GitHub authorization was not completed');return data;}
async function exchange(fetchImpl,config,grant){const data=await githubJson(fetchImpl,GITHUB_TOKEN,{method:'POST',headers:{Accept:'application/json','Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({client_id:config.clientId,client_secret:config.clientSecret,...grant})});if(!TOKEN.test(data.access_token)||!REFRESH.test(data.refresh_token)||!Number.isFinite(data.expires_in)||!Number.isFinite(data.refresh_token_expires_in))throw Error('Expiring GitHub App tokens are required');return data;}
async function verifyOwner(fetchImpl,config,accessToken){const headers={Accept:'application/vnd.github+json',Authorization:'Bearer '+accessToken,'User-Agent':'Paper-Lab-OAuth'};const [user,repo]=await Promise.all([githubJson(fetchImpl,GITHUB_API+'/user',{headers}),githubJson(fetchImpl,GITHUB_API+'/repos/'+config.repository,{headers})]);if(user.login!==config.expectedLogin||repo.full_name!==config.repository||repo.private!==true)throw Error('This GitHub account cannot access the expected private repository');}
function tokenResult(data){return {accessToken:data.access_token,refreshToken:data.refresh_token,expiresIn:data.expires_in,refreshExpiresIn:data.refresh_token_expires_in};}
function popup(res,config,nonce,payload){const scriptNonce=b64(randomBytes(16));const message=JSON.stringify({type:'paper-oauth-result',nonce,...payload}).replace(/</g,'\\u003c');const target=JSON.stringify(config.siteOrigin);res.writeHead(200,{'Content-Type':'text/html; charset=utf-8',...safeHeaders,'Set-Cookie':clearCookie,'Content-Security-Policy':`default-src 'none'; script-src 'nonce-${scriptNonce}'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`});res.end(`<!doctype html><html lang="zh"><meta charset="utf-8"><title>Paper GitHub 登录</title><p>正在返回论文学习站…</p><script nonce="${scriptNonce}">history.replaceState(null,'','/callback');if(window.opener){window.opener.postMessage(${message},${target});window.close()}else{document.querySelector('p').textContent='请返回原页面重新打开登录窗口。'}</script></html>`);}
async function bodyJson(req){let size=0,chunks=[];for await(const chunk of req){size+=chunk.length;if(size>8192)throw Error('Request too large');chunks.push(chunk);}return JSON.parse(Buffer.concat(chunks).toString('utf8'));}

export function createGateway(config,{fetchImpl=fetch}={}){
  return createServer(async(req,res)=>{
    Object.entries(safeHeaders).forEach(([k,v])=>res.setHeader(k,v));
    const url=new URL(req.url||'/',config.baseUrl);
    if(url.pathname==='/health'&&req.method==='GET')return json(res,200,{status:'ready'});
    if(url.pathname==='/auth/config'&&req.method==='GET')return json(res,200,{mode:'github-app',repository:REPOSITORY});
    if(url.pathname==='/start'&&req.method==='GET'){
      const nonce=url.searchParams.get('nonce');if(!nonce||! /^[A-Za-z0-9_-]{24,100}$/.test(nonce))return plainError(res,400,'Invalid login request');
      const state=b64(randomBytes(32)),verifier=b64(randomBytes(32));
      const challenge=b64(createHash('sha256').update(verifier).digest());
      const authorize=new URL(GITHUB_AUTHORIZE);authorize.search=new URLSearchParams({client_id:config.clientId,redirect_uri:config.baseUrl+'/callback',state,code_challenge:challenge,code_challenge_method:'S256',allow_signup:'false'}).toString();
      res.writeHead(302,{...safeHeaders,Location:authorize.toString(),'Set-Cookie':cookieHeader(seal({state,verifier,nonce,at:Date.now()},config.cookieKey))});return res.end();
    }
    if(url.pathname==='/callback'&&req.method==='GET'){
      let state;try{state=unseal(cookieValue(req),config.cookieKey);if(Date.now()-state.at>600000||state.at>Date.now()+30000||!fixed(state.state,url.searchParams.get('state')))throw Error('Invalid OAuth state');}catch{return plainError(res,400,'Login request expired or did not match');}
      if(url.searchParams.get('error'))return popup(res,config,state.nonce,{error:'GitHub authorization was declined'});
      const code=url.searchParams.get('code');if(!code||code.length>500)return plainError(res,400,'GitHub did not provide a valid code');
      try{const tokens=await exchange(fetchImpl,config,{code,redirect_uri:config.baseUrl+'/callback',code_verifier:state.verifier});await verifyOwner(fetchImpl,config,tokens.access_token);return popup(res,config,state.nonce,tokenResult(tokens));}
      catch{return popup(res,config,state.nonce,{error:'GitHub account or repository permission could not be verified'});}
    }
    if(url.pathname==='/refresh'){
      const origin=req.headers.origin;if(origin!==config.siteOrigin)return plainError(res,403,'Origin not allowed');
      const cors={'Access-Control-Allow-Origin':config.siteOrigin,'Vary':'Origin','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type'};
      if(req.method==='OPTIONS'){res.writeHead(204,{...safeHeaders,...cors});return res.end();}
      if(req.method!=='POST')return plainError(res,405,'Method not allowed');
      if(!String(req.headers['content-type']||'').startsWith('application/json'))return plainError(res,415,'JSON required');
      try{const body=await bodyJson(req);if(!REFRESH.test(body.refreshToken))return json(res,400,{error:'Invalid refresh credential'},cors);const tokens=await exchange(fetchImpl,config,{grant_type:'refresh_token',refresh_token:body.refreshToken});await verifyOwner(fetchImpl,config,tokens.access_token);return json(res,200,tokenResult(tokens),cors);}
      catch{return json(res,401,{error:'Session expired; sign in again'},cors);}
    }
    return serveSite(req,res,config.siteDir,url.pathname);
  });
}

if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
  const config=checkedConfig();if(!config.siteDir)throw Error('PAPER_SITE_DIR is required to serve Paper at the same origin');const port=Number(process.env.PORT||3000);createGateway(config).listen(port,'0.0.0.0');
}
