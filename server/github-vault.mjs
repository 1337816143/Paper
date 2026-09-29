import {createHash,randomUUID} from 'node:crypto';
export const REPOSITORY='1337816143/My-Evolution';
export const DATA_BRANCH='paper-user-data';
export const PREFIX='private/paper-sync/v5/';
const ROOT='/repos/'+REPOSITORY, names=['GH_TOKEN_PRIMARY','GH_TOKEN_SECONDARY'];
const pause=ms=>new Promise(r=>setTimeout(r,ms));
export const digest=b=>createHash('sha256').update(b).digest('hex');
export const problem=(status,message)=>Object.assign(new Error(message),{status});
let active='',queue=Promise.resolve();
export let report={ready:false,tokens:[],selected:null};
async function request(path,{method='GET',body,credential=active,missing=false}={}){
 if(!credential)throw problem(503,'服务端授权尚未就绪。');
 if(path!==ROOT&&!path.startsWith(ROOT+'/'))throw problem(403,'只允许固定私有仓库。');
 const run=async()=>{const response=await fetch('https://api.github.com'+path,{method,redirect:'error',headers:{Authorization:'Bearer '+credential,Accept:'application/vnd.github+json','Content-Type':'application/json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Paper-Private-Vault/5.2'},body:body?JSON.stringify(body):undefined,signal:AbortSignal.timeout(45000)});
 if(response.status===404&&missing)return null;
 if(!response.ok)throw problem(response.status,'GitHub request HTTP '+response.status);
 return response.status===204?null:response.json();};
 if(method==='GET')return run();
 const promise=queue.then(async()=>{await pause(1100);return run();});queue=promise.catch(()=>{});return promise;
}
function branchOK(branch){if(branch!==DATA_BRANCH&&!/^paper-user-data-test-\d+$/.test(branch))throw problem(403,'不允许的数据分支。');}
function pathOK(path){if(!/^private\/paper-sync\/v5\/(?:index\.json|objects\/[a-f0-9]{64}\.bin|devices\/[A-Za-z0-9-]{1,90}\.json)$/.test(path))throw problem(403,'不允许的私有数据路径。');}
export async function verifyPrivate(){const info=await request(ROOT);if(info.private!==true)throw problem(403,'目标仓库必须私有。');return {private:true,full_name:REPOSITORY,permissions:{pull:true,push:true}};}
export async function branchInfo(branch=DATA_BRANCH){branchOK(branch);return request(ROOT+'/branches/'+branch);}
export async function readData(path,branch=DATA_BRANCH,missing=false){pathOK(path);branchOK(branch);return request(ROOT+'/contents/'+path+'?ref='+branch,{missing});}
export async function writeData(path,base64,sha,branch=DATA_BRANCH){
 pathOK(path);branchOK(branch);
 if(typeof base64!=='string'||base64.length>750000||!/^[A-Za-z0-9+/]*={0,2}$/.test(base64)||sha&&!/^[a-f0-9]{40}$/.test(sha))throw problem(400,'无效分块或版本号。');
 const bytes=Buffer.from(base64,'base64');if(bytes.length>524288||bytes.toString('base64')!==base64)throw problem(400,'分块过大或编码有误。');
 if(path.includes('/objects/')&&digest(bytes)!==path.split('/').pop().slice(0,-4))throw problem(400,'分块哈希不匹配。');
 await verifyPrivate();
 return request(ROOT+'/contents/'+path,{method:'PUT',body:{branch,content:base64,message:'Paper private checkpoint [skip ci]',...(sha?{sha}:{})}});
}
// Auth state contains hashes and device metadata, never GitHub credentials or raw invitations.
const AUTH='private/paper-sync-auth/v52/';
function authPath(id){if(!/^(?:devices|invites)\/[a-f0-9-]{32,64}$/.test(id))throw problem(403,'无效授权记录');return AUTH+id+'.json';}
export async function authRead(id,missing=false){const r=await request(ROOT+'/contents/'+authPath(id)+'?ref='+DATA_BRANCH,{missing});return r?{value:JSON.parse(Buffer.from(r.content.replace(/\s/g,''),'base64').toString()),sha:r.sha}:null;}
export async function authWrite(id,value,sha){return request(ROOT+'/contents/'+authPath(id),{method:'PUT',body:{branch:DATA_BRANCH,content:Buffer.from(JSON.stringify(value)).toString('base64'),message:'Paper device authorization metadata [skip ci]',...(sha?{sha}:{})}});}
export async function initialize(){
 const results=[];
 for(let i=0;i<names.length;i++){
  const credential=process.env[names[i]],r={label:'token-'+(i+1),provided:!!credential,privateRepositoryRead:false,readBack:false,write:false,cleanup:false,actionsRead:false,usable:false};
  let path='',sha='';
  if(credential)try{
   const info=await request(ROOT,{credential});r.privateRepositoryRead=info.private===true;r.reportedPermissions=info.permissions||null;r.ownerVerified=String(info.owner?.id)==='201706309';
   if(!r.privateRepositoryRead||!r.ownerVerified)throw problem(403,'Wrong repository');
   await request(ROOT+'/branches/'+DATA_BRANCH,{credential});
   path=PREFIX+'devices/probe-'+randomUUID()+'.json';const content=Buffer.from(JSON.stringify({synthetic:true,purpose:'private write verification',at:Date.now()})).toString('base64');
   const write=await request(ROOT+'/contents/'+path,{credential,method:'PUT',body:{branch:DATA_BRANCH,content,message:'Verify private synchronization permission [skip ci]'}});sha=write.content.sha;r.write=true;
   const back=await request(ROOT+'/contents/'+path+'?ref='+DATA_BRANCH,{credential});r.readBack=back.content.replace(/\s/g,'')===content;
   await request(ROOT+'/contents/'+path,{credential,method:'DELETE',body:{branch:DATA_BRANCH,sha,message:'Remove synthetic permission probe [skip ci]'}});sha='';r.cleanup=true;
   try{await request(ROOT+'/actions/workflows?per_page=1',{credential});r.actionsRead=true;}catch{}
   r.usable=r.privateRepositoryRead&&r.ownerVerified&&r.readBack&&r.write&&r.cleanup;
  }catch(e){r.failureHTTP=e.status||0;}
  finally{if(sha)try{await request(ROOT+'/contents/'+path,{credential,method:'DELETE',body:{branch:DATA_BRANCH,sha,message:'Clean permission probe [skip ci]'}});r.cleanup=true;}catch{r.cleanupPending=true;}}
  results.push(r);
 }
 const choices=results.map((r,i)=>({r,i,score:(r.reportedPermissions?.admin?100:0)+(r.actionsRead?10:0)})).filter(x=>x.r.usable).sort((a,b)=>b.score-a.score||a.i-b.i);
 if(choices.length){active=process.env[names[choices[0].i]];report={ready:true,tokens:results,selected:choices[0].r.label};}
 else report={ready:false,tokens:results,selected:null};
 console.log(JSON.stringify({event:'permission-verification',...report}));return report;
}
