import {createHmac,timingSafeEqual,randomBytes,randomUUID,createPublicKey,verify} from 'node:crypto';
import {authRead,authWrite,digest,problem,branchInfo,DATA_BRANCH,REPOSITORY} from './github-vault.mjs';
const DAY=86400000,deviceCache=new Map();let jwks=null,jwksAt=0;
const constant=(a,b)=>{const x=Buffer.from(a),y=Buffer.from(b);return x.length===y.length&&timingSafeEqual(x,y);};
function key(){const secret=process.env.GH_TOKEN_PRIMARY||process.env.GH_TOKEN_SECONDARY;if(!secret)throw problem(503,'Server authorization missing');return createHmac('sha256',secret).update('paper-managed-device-sessions-v52').digest();}
const permittedBranch=b=>b===DATA_BRANCH||/^paper-user-data-test-\d+$/.test(b);
function sign(v){const p=Buffer.from(JSON.stringify(v)).toString('base64url');return 'pds1.'+p+'.'+createHmac('sha256',key()).update(p).digest('base64url');}
function decode(token){
 if(typeof token!=='string'||token.length>4096)throw problem(401,'此设备尚未授权。');
 const [prefix,p,mac,extra]=token.split('.');if(prefix!=='pds1'||!p||!mac||extra||!constant(mac,createHmac('sha256',key()).update(p).digest('base64url')))throw problem(401,'设备会话无效。');
 let v;try{v=JSON.parse(Buffer.from(p,'base64url'));}catch{throw problem(401,'会话格式无效。');}
 if(v.v!==1||v.owner!=='201706309'||!permittedBranch(v.branch)||!/^[a-f0-9-]{36}$/.test(v.id)||!Number.isSafeInteger(v.exp)||v.exp<Date.now())throw problem(401,'设备授权已过期。');return v;
}
export async function authenticate(header){const token=String(header||'').replace(/^Bearer /,'');const v=decode(token);let row=deviceCache.get(v.id);if(!row||row.at<Date.now()-60000){const found=await authRead('devices/'+v.id);row={at:Date.now(),...found};deviceCache.set(v.id,row);}if(row.value.revoked||row.value.branch!==v.branch||row.value.expiresAt<Date.now())throw problem(401,'设备已退出或授权过期。');return {...v,token};}
export async function newSession(branch,label){if(!permittedBranch(branch))throw problem(403,'Invalid device scope');await branchInfo(branch);const id=randomUUID(),exp=Date.now()+90*DAY;await authWrite('devices/'+id,{id,branch,label:String(label||'个人设备').slice(0,80),createdAt:Date.now(),expiresAt:exp,revoked:false});return {token:sign({v:1,owner:'201706309',id,branch,exp}),expiresAt:exp,deviceId:id,configuration:{repository:REPOSITORY,branch}};}
export async function createInvite(branch,label,seconds=600){
 if(!permittedBranch(branch))throw problem(403,'Invalid invitation scope');const grant=randomBytes(32).toString('base64url'),expiresAt=Date.now()+Math.min(seconds,604800)*1000;
 await authWrite('invites/'+digest(grant),{branch,label:String(label||'个人设备').slice(0,80),expiresAt,used:false});return {grant,expiresAt,url:'https://1337816143.github.io/Paper/#/activate/'+grant};
}
export async function exchange(grant,label){if(typeof grant!=='string'||!/^[\w-]{43}$/.test(grant))throw problem(401,'授权邀请格式不正确。');const id='invites/'+digest(grant),row=await authRead(id,true);if(!row||row.value.used||row.value.expiresAt<Date.now())throw problem(401,'邀请已使用或过期，请在已连接设备生成新邀请。');try{await authWrite(id,{...row.value,used:true,usedAt:Date.now()},row.sha);}catch(e){if(e.status===409||e.status===422)throw problem(401,'此邀请已经被使用。');throw e;}return newSession(row.value.branch,label||row.value.label);}
export async function renew(user){if(user.exp>Date.now()+30*DAY)return {token:user.token,expiresAt:user.exp,deviceId:user.id,configuration:{repository:REPOSITORY,branch:user.branch}};const row=await authRead('devices/'+user.id),exp=Date.now()+90*DAY;await authWrite('devices/'+user.id,{...row.value,expiresAt:exp},row.sha);deviceCache.delete(user.id);return {token:sign({v:1,owner:'201706309',id:user.id,branch:user.branch,exp}),expiresAt:exp,deviceId:user.id,configuration:{repository:REPOSITORY,branch:user.branch}};}
export async function revoke(user){const row=await authRead('devices/'+user.id);await authWrite('devices/'+user.id,{...row.value,revoked:true,revokedAt:Date.now()},row.sha);deviceCache.delete(user.id);return {revoked:true};}

// Bootstrap is limited to a single named workflow in the owner's PRIVATE repository.
// No public workflow or browser-supplied identity can mint a device invitation.
export async function trustedWorkflow(header){
 const token=String(header||'').replace(/^Bearer /,'');if(token.length>18000)throw problem(401,'Invalid workflow identity');const pieces=token.split('.');if(pieces.length!==3)throw problem(401,'Workflow identity required');
 let h,c;try{h=JSON.parse(Buffer.from(pieces[0],'base64url'));c=JSON.parse(Buffer.from(pieces[1],'base64url'));}catch{throw problem(401,'Invalid identity');}
 if(h.alg!=='RS256'||c.iss!=='https://token.actions.githubusercontent.com'||c.aud!=='paper-managed-sync-v52'||String(c.repository_id)!=='1315637011'||String(c.repository_owner_id)!=='201706309'||c.repository!==REPOSITORY||!['push','workflow_dispatch'].includes(c.event_name)||!['refs/heads/paper-managed-sync-validation','refs/heads/main'].includes(c.ref)||c.workflow_ref!==REPOSITORY+'/.github/workflows/paper-managed-sync.yml@'+c.ref||!Number.isFinite(c.exp)||c.exp*1000<Date.now()||c.iat*1000>Date.now()+30000||Date.now()-c.iat*1000>600000)throw problem(403,'Untrusted workflow');
 if(!jwks||Date.now()-jwksAt>3600000){const r=await fetch('https://token.actions.githubusercontent.com/.well-known/jwks',{redirect:'error',signal:AbortSignal.timeout(15000)});if(!r.ok)throw problem(503,'Identity issuer unavailable');jwks=await r.json();jwksAt=Date.now();}
 const jwk=jwks.keys.find(k=>k.kid===h.kid);if(!jwk||!verify('RSA-SHA256',Buffer.from(pieces[0]+'.'+pieces[1]),createPublicKey({key:jwk,format:'jwk'}),Buffer.from(pieces[2],'base64url')))throw problem(401,'Invalid identity signature');return c;
}
