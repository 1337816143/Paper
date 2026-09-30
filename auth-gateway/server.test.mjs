import test from 'node:test';
import assert from 'node:assert/strict';
import {once} from 'node:events';
import {checkedConfig,createGateway} from './server.mjs';

const ACCESS='ghu_'+ 'A'.repeat(40);
const REFRESH='ghr_'+ 'B'.repeat(40);
const config=()=>checkedConfig({
  GITHUB_APP_CLIENT_ID:'Iv1.synthetic',GITHUB_APP_CLIENT_SECRET:'synthetic-client-secret',
  COOKIE_KEY_BASE64URL:Buffer.alloc(32,7).toString('base64url'),
  PUBLIC_BASE_URL:'http://127.0.0.1:4173',PAPER_SITE_ORIGIN:'http://127.0.0.1:4173',ALLOW_INSECURE_LOCAL:'1'
});
const mockGithub=(login='1337816143')=>async(url,options={})=>{
  if(url.endsWith('/login/oauth/access_token')){
    const body=String(options.body);
    assert.ok(body.includes('client_secret=synthetic-client-secret'));
    return Response.json({access_token:ACCESS,refresh_token:REFRESH,expires_in:28800,refresh_token_expires_in:15552000});
  }
  if(url.endsWith('/user'))return Response.json({login});
  if(url.endsWith('/repos/1337816143/My-Evolution'))return Response.json({full_name:'1337816143/My-Evolution',private:true});
  throw Error('Unexpected mock URL: '+url);
};
async function withGateway(fn,{login}={}){
  const server=createGateway(config(),{fetchImpl:mockGithub(login)});server.listen(0,'127.0.0.1');await once(server,'listening');
  const url='http://127.0.0.1:'+server.address().port;
  try{return await fn(url);}finally{server.close();await once(server,'close');}
}

test('deployment rejects shared GitHub Pages origins and missing credentials',()=>{
  assert.throws(()=>checkedConfig({}),/credentials/);
  const env={GITHUB_APP_CLIENT_ID:'x',GITHUB_APP_CLIENT_SECRET:'y',COOKIE_KEY_BASE64URL:Buffer.alloc(32).toString('base64url'),PUBLIC_BASE_URL:'https://1337816143.github.io',PAPER_SITE_ORIGIN:'https://1337816143.github.io'};
  assert.throws(()=>checkedConfig(env),/dedicated same-origin/);
});

test('web flow binds state and PKCE to a short-lived secure cookie',()=>withGateway(async base=>{
  const start=await fetch(base+'/start?nonce='+ 'n'.repeat(32),{redirect:'manual'});
  assert.equal(start.status,302);
  const target=new URL(start.headers.get('location'));
  assert.equal(target.origin,'https://github.com');
  assert.equal(target.searchParams.get('code_challenge_method'),'S256');
  assert.ok(target.searchParams.get('state'));
  const cookie=start.headers.get('set-cookie');
  assert.match(cookie,/HttpOnly; Secure; SameSite=Lax/);
  const bad=await fetch(base+'/callback?code=synthetic&state=wrong',{headers:{Cookie:cookie}});
  assert.equal(bad.status,400);
  const callback=await fetch(base+'/callback?code=synthetic&state='+target.searchParams.get('state'),{headers:{Cookie:cookie}});
  const html=await callback.text();
  assert.equal(callback.status,200);
  assert.match(html,/paper-oauth-result/);
  assert.match(html,/ghu_A{40}/);
  assert.match(html,/ghr_B{40}/);
  assert.doesNotMatch(html,/synthetic-client-secret/);
  assert.match(callback.headers.get('content-security-policy'),/frame-ancestors 'none'/);
}));

test('callback rejects a different account before disclosing tokens',()=>withGateway(async base=>{
  const start=await fetch(base+'/start?nonce='+ 'n'.repeat(32),{redirect:'manual'});
  const state=new URL(start.headers.get('location')).searchParams.get('state');
  const callback=await fetch(base+'/callback?code=synthetic&state='+state,{headers:{Cookie:start.headers.get('set-cookie')}});
  const html=await callback.text();
  assert.match(html,/permission could not be verified/);
  assert.doesNotMatch(html,/ghu_A{40}/);
},{login:'wrong-user'}));

test('refresh requires the exact origin and rotates through the server secret',()=>withGateway(async base=>{
  const wrong=await fetch(base+'/refresh',{method:'POST',headers:{Origin:'https://attacker.example','Content-Type':'application/json'},body:JSON.stringify({refreshToken:REFRESH})});
  assert.equal(wrong.status,403);
  const preflight=await fetch(base+'/refresh',{method:'OPTIONS',headers:{Origin:config().siteOrigin}});
  assert.equal(preflight.status,204);
  const good=await fetch(base+'/refresh',{method:'POST',headers:{Origin:config().siteOrigin,'Content-Type':'application/json'},body:JSON.stringify({refreshToken:REFRESH})});
  assert.equal(good.status,200);
  assert.equal(good.headers.get('access-control-allow-origin'),config().siteOrigin);
  assert.equal((await good.json()).accessToken,ACCESS);
}));
import {mkdtemp,mkdir,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

test('gateway serves the Paper site at the OAuth origin with bounded paths and CSP',async()=>{
  const site=await mkdtemp(join(tmpdir(),'paper-site-'));
  try{
    await writeFile(join(site,'index.html'),'<title>Paper</title>');
    await writeFile(join(site,'style.css'),'body{}');
    await mkdir(join(site,'downloads'));
    await writeFile(join(site,'downloads','Paper-Lab-offline.html'),'<script>offline()</script>');
    const server=createGateway({...config(),siteDir:site},{fetchImpl:mockGithub()});
    server.listen(0,'127.0.0.1');await once(server,'listening');
    const base='http://127.0.0.1:'+server.address().port;
    try{
      const marker=await fetch(base+'/auth/config');
      assert.deepEqual(await marker.json(),{mode:'github-app',repository:'1337816143/My-Evolution'});
      const home=await fetch(base+'/');
      assert.equal(home.status,200);
      assert.equal(await home.text(),'<title>Paper</title>');
      assert.match(home.headers.get('content-security-policy'),/script-src 'self'/);
      const css=await fetch(base+'/style.css');
      assert.equal(css.headers.get('content-type'),'text/css; charset=utf-8');
      assert.equal(await css.text(),'body{}');
      assert.equal((await fetch(base+'/.env')).status,404);
      assert.equal((await fetch(base+'/%2e%2e/%2e%2e/secrets')).status,404);
      const offline=await fetch(base+'/downloads/Paper-Lab-offline.html');
      assert.match(offline.headers.get('content-disposition'),/^attachment/);
      assert.equal((await fetch(base+'/style.css',{method:'HEAD'})).status,200);
    }finally{server.close();await once(server,'close');}
  }finally{await rm(site,{recursive:true,force:true});}
});
