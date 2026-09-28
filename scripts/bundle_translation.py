"""Preparation only: bundle pinned public npm code; no source text or notes leave device."""
from pathlib import Path
import subprocess,json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'vendor/translation';tmp=Path('/tmp/paper-inference-bundle');tmp.mkdir(exist_ok=True)
subprocess.run(['npm','install','--prefix',str(tmp),'--ignore-scripts','--no-audit','--no-fund','@huggingface/transformers@3.8.1','esbuild@0.25.10'],check=True)
entry=tmp/'node_modules/@huggingface/transformers/dist/transformers.web.min.js'
subprocess.run([str(tmp/'node_modules/.bin/esbuild'),str(entry),'--bundle','--platform=browser','--format=esm','--minify','--legal-comments=inline','--outfile='+str(out/'transformers.web.min.js')],check=True)
for package,name in [('onnxruntime-common','ONNXRUNTIME-LICENSE'),('onnxruntime-web','ONNXRUNTIME-WEB-LICENSE')]:
 for filename in ['LICENSE','LICENSE.txt','LICENSE.md']:
  p=tmp/'node_modules'/package/filename
  if p.exists():shutil.copyfile(p,out/name);break
m=json.loads((out/'manifest.json').read_text());m['bundler']='esbuild@0.25.10; all JavaScript imports bundled for native module worker';m['files']=[]
for p in sorted(out.rglob('*')):
 if p.is_file() and p.name!='manifest.json':
  assert p.suffix.lower() not in ['.ttf','.otf','.woff','.woff2']
  m['files'].append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
m['totalBytes']=sum(f['bytes'] for f in m['files']);(out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
print('Fully bundled local browser runtime:',(out/'transformers.web.min.js').stat().st_size,'bytes; total public translation assets:',m['totalBytes'])
