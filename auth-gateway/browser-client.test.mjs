import test from 'node:test';
import assert from 'node:assert/strict';
import {webcrypto} from 'node:crypto';
import {createOAuthClient} from './browser-client.mjs';

const ACCESS='ghu_'+ 'A'.repeat(40),REFRESH='ghr_'+ 'B'.repeat(40);
const ROTATED='ghr_'+ 'C'.repeat(40),ORIGIN='https://paper.example';
function fixture(){
  const calls=[];let saved=null,connected=false;
  const store={read:async()=>saved,save:async data=>{saved=data;calls.push(['save',data]);},clear:async()=>{saved=null;}};
  const sync={status:()=>({busy:false,connected}),disconnect:()=>{connected=false;calls.push(['disconnect']);},connect:async(config,token)=>{calls.push(['connect',config,token]);connected=true;return {state:'synced'};}};
  return {calls,store,sync,saved:()=>saved};
}

test('client requires an isolated Paper origin',()=>{
  const f=fixture();assert.throws(()=>createOAuthClient({gateway:'https://1337816143.github.io',siteOrigin:'https://1337816143.github.io',sync:f.sync,store:f.store,popupOpen:()=>null,eventTarget:new EventTarget()}),/dedicated/);
});

test('new-device login accepts only its popup, origin and nonce, then saves refresh only',async()=>{
  const f=fixture(),events=new EventTarget(),popup={closed:false};let startUrl;
  const client=createOAuthClient({gateway:ORIGIN,siteOrigin:ORIGIN,sync:f.sync,store:f.store,cryptoImpl:webcrypto,eventTarget:events,popupOpen:url=>{startUrl=url;return popup;}});
  const promise=client.login(),nonce=new URL(startUrl).searchParams.get('nonce');
  const send=(origin,source,replyNonce)=>{const event=new Event('message');Object.assign(event,{origin,source,data:{type:'paper-oauth-result',nonce:replyNonce,accessToken:ACCESS,refreshToken:REFRESH,expiresIn:28800,refreshExpiresIn:15552000}});events.dispatchEvent(event);};
  send('https://attacker.example',popup,nonce);send(ORIGIN,{},nonce);send(ORIGIN,popup,'wrong');
  assert.equal(f.calls.length,0);
  send(ORIGIN,popup,nonce);await promise;
  assert.ok(f.saved().refreshToken===REFRESH);
  assert.ok(!JSON.stringify(f.saved()).includes(ACCESS));
  assert.deepEqual(f.calls.at(-1),['connect',{repository:'1337816143/My-Evolution',branch:'paper-user-data'},ACCESS]);
  await client.forget();
});

test('refresh rotates credential before reconnecting and never stores access token',async()=>{
  const f=fixture();await f.store.save({refreshToken:REFRESH,expiresAt:Date.now()+100000});f.calls.length=0;
  const client=createOAuthClient({gateway:ORIGIN,siteOrigin:ORIGIN,sync:f.sync,store:f.store,cryptoImpl:webcrypto,eventTarget:new EventTarget(),popupOpen:()=>null,fetchImpl:async(url,options)=>{assert.equal(url,ORIGIN+'/refresh');assert.equal(JSON.parse(options.body).refreshToken,REFRESH);return Response.json({accessToken:ACCESS,refreshToken:ROTATED,expiresIn:28800,refreshExpiresIn:15552000});}});
  await client.resume();
  assert.equal(f.saved().refreshToken,ROTATED);
  assert.deepEqual(f.calls.map(x=>x[0]),['save','connect']);
  assert.ok(!JSON.stringify(f.saved()).includes(ACCESS));
  await client.forget();
});
