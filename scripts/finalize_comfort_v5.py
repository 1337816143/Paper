"""Final browser review fixes. Server-side permission enforcement remains authoritative."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def patch(path,old,new):
 p=ROOT/path;s=p.read_text()
 if new in s:return
 assert old in s,(path,old[:70]);p.write_text(s.replace(old,new,1))
p=ROOT/'src/sync.js';s=p.read_text();old=r'/^(?:github_pat_|gh[opusr]_)[A-Za-z0-9_]{16,}$/';new=r'/^(?:github_pat_|gh[opusr]_)[A-Za-z0-9_.-]{16,4096}$/'
# Current GitHub installation tokens can contain JWT punctuation. Keep them opaque.
if old in s:s=s.replace(old,new,1)
else:assert new in s,'Authorization validation changed'
# Use GitHub's documented default 2022-11-28 API in browser CORS requests.
s=s.replace("'X-GitHub-Api-Version':'2022-11-28',",'')
# Repository collaborator role flags are not a token's endpoint permission set.
# Before accepting a connection, an actual Contents write is required below.
s=s.replace("if(info.permissions&&info.permissions.push===false)throw Error('此授权没有仓库写入权限。');",'')
p.write_text(s)
patch('src/sync.js',"if(!path.startsWith('/repos/'+config.repository+'/'))throw Error('拒绝访问同步仓库之外的路径');", "const root='/repos/'+config.repository;if(path!==root&&!path.startsWith(root+'/'))throw Error('拒绝访问同步仓库之外的路径');")
patch('src/sync.js',"const route=path=>'/repos/'+config.repository+'/'+path;", "const route=path=>'/repos/'+config.repository+(path?'/'+path:'');")
patch('src/sync.js',"}catch(e){if(e.name==='AbortError')throw Error('GitHub 请求超时；本地更改和已上传分块保留。');throw e;}", "}catch(e){if(e.name==='AbortError')throw Error('GitHub 请求超时；本地更改和已上传分块保留。');if(e instanceof TypeError)throw Error('浏览器未能连接 GitHub API，请检查网络或浏览器跨域错误；本地更改未删除，也未标记云端完成。');throw e;}")
patch('src/sync.js',"async function connect(c,token){", """async function verifyWriteAccess(){const path=PREFIX+'devices/'+device+'.json',prior=await getFile(path,true);const data=encoder.encode(JSON.stringify({schema:'paper.private.device.v5',device,at:new Date().toISOString(),purpose:'Authorized private data checkpoint; no credentials'}));await putFile(path,data,prior?.sha);const check=await getFile(path);if(check?.encoding!=='base64'||await sha(unbase64(check.content))!==await sha(data))throw Error('GitHub 写入确认不一致；未建立同步连接。');}
async function connect(c,token){""")
patch('src/sync.js',"try{await verifyVault();localStorage.setItem('paper-sync-config-v5'", "try{await verifyVault();await verifyWriteAccess();localStorage.setItem('paper-sync-config-v5'")
for name in ['src/reader.js','src/app.js','src/study.js','src/workspace.js']:
 p=ROOT/name;s=p.read_text()
 for a,b in {
  '笔记只保存在本设备。':'笔记先保存本地；连接 GitHub 私有同步后可跨设备恢复。',
  '仅保存本机；不会上传到公开仓库。建议定期导出。':'本地优先保存；连接 GitHub 后同步至私有数据分支，不进入公开网站。建议定期导出。',
  '本机保存；不会上传GitHub或发送给第三方。':'本地优先保存；云端是否已确认请查看顶部 GitHub 同步状态。',
  '仅保存本机，建议定期导出。':'本地优先保存；连接私有同步后可跨设备恢复，建议定期导出。',
  '数据仅保存在此浏览器；导出后可备份或导入其他设备。':'数据本地优先保存；可连接 GitHub 私有同步，或导出备份后导入其他设备。',
  '本机保存，不会上传。':'本地优先保存；连接私有同步后写入 GitHub 数据分支。',
  '仅保存本机。英文原文和原有批注不改变；':'校订先保存本机，连接私有同步后可跨设备恢复。英文原文和原有批注不改变；'
 }.items():s=s.replace(a,b)
 p.write_text(s)
p=ROOT/'src/comfort.css';s=p.read_text();extra='\n/* Keep the editor readable even above dense text; glass remains at its edge. */\n.context-popover{background:color-mix(in srgb,var(--paper) 95%,transparent)}\n'
if extra not in s:p.write_text(s+extra)
p=ROOT/'scripts/test_v5.py';s=p.read_text();s=s.replace("secret='ghs_'+'SyntheticSessionOnlyForTests123456789'","secret='ghs_123_'+'SyntheticJWT.Header-Payload.SignatureOnlyForTests123456789'")
s=s.replace("'permissions':{'push':True}","'permissions':{'push':False}")
# Endpoint denials still prevent connection even when repository metadata is readable.
s=s.replace("if request.method=='GET':", "if request.method!='GET' and fault.get('denyWrite'):return reply(403,{'message':'Synthetic endpoint Contents permission denial'})\n if request.method=='GET':") if "fault.get('denyWrite')" not in s else s
old="writes=fault['writes'];result=pa.evaluate"
new="""pa.evaluate('PaperSync.disconnect()');fault['denyWrite']=True
  denied=pa.evaluate(\"async token=>{try{await PaperSync.connect({repository:'paper-tests/private',branch:'paper-user-data'},token);return false;}catch{return !PaperSync.status().connected&&PaperSync.status().state==='error';}}\",secret)
  assert denied;fault['denyWrite']=False;checks.append('Actual Contents write denial blocks connection despite readable private repository metadata')
  writes=fault['writes'];result=pa.evaluate"""
if new not in s:
 assert old in s;s=s.replace(old,new,1)
p.write_text(s)
print('Connection requires verified private Contents write/read-back; role flags do not substitute for endpoint authorization.')
