// Browser-side OAuth controller for a dedicated Paper origin. Access tokens stay
// in PaperSync page memory; only the rotating refresh credential is encrypted
// in a device-only IndexedDB store. Never include this database in backups.
const REPOSITORY='1337816143/My-Evolution';
const BRANCH='paper-user-data';
const ACCESS=/^gh[opusr]_[A-Za-z0-9_.-]{16,4096}$/;
const REFRESH=/^ghr_[A-Za-z0-9_.-]{16,4096}$/;
const b64=bytes=>btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');

export function encryptedDeviceStore({indexedDB,crypto}){
  let database;
  async function db(){if(database)return database;database=await new Promise((resolve,reject)=>{const request=indexedDB.open('paper-oauth-device-v1',1);request.onupgradeneeded=()=>request.result.createObjectStore('session',{keyPath:'id'});request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);});return database;}
  async function op(mode,method,value){const d=await db();return new Promise((resolve,reject)=>{const tx=d.transaction('session',mode),request=tx.objectStore('session')[method](value);let result;request.onsuccess=()=>result=request.result;tx.oncomplete=()=>resolve(result);tx.onerror=tx.onabort=()=>reject(Error('This device could not save the login credential'));});}
  return {
    async read(){const row=await op('readonly','get','active');if(!row)return null;const plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:row.iv,additionalData:new TextEncoder().encode('PaperLab.github-app.v1')},row.key,row.ciphertext);const data=JSON.parse(new TextDecoder().decode(plain));if(!REFRESH.test(data.refreshToken)||!Number.isFinite(data.expiresAt))throw Error('Saved authorization is invalid');return data;},
    async save(data){if(!REFRESH.test(data.refreshToken)||!Number.isFinite(data.expiresAt))throw Error('Invalid refresh credential');const prior=await op('readonly','get','active');const key=prior?.key||await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);if(key.extractable)throw Error('Device key must not be extractable');const iv=crypto.getRandomValues(new Uint8Array(12));const ciphertext=await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:new TextEncoder().encode('PaperLab.github-app.v1')},key,new TextEncoder().encode(JSON.stringify(data)));await op('readwrite','put',{id:'active',key,iv,ciphertext});},
    async clear(){await op('readwrite','delete','active');}
  };
}

export function createOAuthClient({gateway,siteOrigin,sync,store,fetchImpl=fetch,popupOpen=window.open.bind(window),eventTarget=window,cryptoImpl=globalThis.crypto,now=Date.now}){
  if(gateway!==siteOrigin||new URL(gateway).hostname.endsWith('.github.io'))throw Error('OAuth requires a dedicated same-origin Paper host');
  let pending=null,refreshing=null,timer=null,expiresAt=0,connected=false;
  const status=()=>({configured:true,connected,pending:!!pending,expiresAt});
  function schedule(seconds){clearTimeout(timer);const delay=Math.max(30000,(seconds-300)*1000);timer=setTimeout(()=>resume().catch(()=>{}),delay);}
  async function connect(tokens){if(!ACCESS.test(tokens.accessToken)||!REFRESH.test(tokens.refreshToken)||!Number.isFinite(tokens.expiresIn)||tokens.expiresIn<60||!Number.isFinite(tokens.refreshExpiresIn))throw Error('GitHub returned invalid expiring credentials');
    // GitHub invalidates the prior refresh token immediately; persist the new
    // credential before connecting. A failed write requires a fresh login.
    await store.save({refreshToken:tokens.refreshToken,expiresAt:now()+tokens.refreshExpiresIn*1000});
    const deadline=now()+30000;while(sync.status().busy){if(now()>deadline)throw Error('Wait for the current sync to finish before reconnecting');await new Promise(resolve=>setTimeout(resolve,500));}
    if(sync.status().connected)sync.disconnect();
    const result=await sync.connect({repository:REPOSITORY,branch:BRANCH},tokens.accessToken);
    connected=true;expiresAt=now()+tokens.expiresIn*1000;schedule(tokens.expiresIn);return result;
  }
  async function login(){if(pending)throw Error('GitHub login is already open');const nonce=b64(cryptoImpl.getRandomValues(new Uint8Array(32)));const popup=popupOpen(gateway+'/start?nonce='+nonce,'paper-github-login','popup,width=550,height=700');if(!popup)throw Error('Allow the login popup to open');
    pending=new Promise((resolve,reject)=>{const timeout=setTimeout(()=>finish(Error('Login timed out')),120000);const closed=setInterval(()=>{if(popup.closed)finish(Error('Login window was closed'));},400);function finish(error,data){clearTimeout(timeout);clearInterval(closed);eventTarget.removeEventListener('message',onMessage);pending=null;if(error)reject(error);else resolve(data);}function onMessage(event){if(event.origin!==siteOrigin||event.source!==popup||event.data?.type!=='paper-oauth-result'||event.data.nonce!==nonce)return;if(event.data.error)return finish(Error(event.data.error));finish(null,event.data);}eventTarget.addEventListener('message',onMessage);});
    return connect(await pending);
  }
  async function resume(){if(refreshing)return refreshing;refreshing=(async()=>{const saved=await store.read();if(!saved)return null;if(saved.expiresAt<=now())throw Error('GitHub login expired; sign in again');const response=await fetchImpl(gateway+'/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({refreshToken:saved.refreshToken}),credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer'});if(response.status===400||response.status===401)throw Error('GitHub login expired; sign in again');if(!response.ok)throw Error('Login service temporarily unavailable');return connect(await response.json());})();try{return await refreshing;}catch(error){if(error.message!=='GitHub login expired; sign in again'){clearTimeout(timer);timer=setTimeout(()=>resume().catch(()=>{}),60000);}throw error;}finally{refreshing=null;}}
  async function forget(){clearTimeout(timer);await store.clear();sync.disconnect();connected=false;expiresAt=0;}
  return {login,resume,forget,status};
}
