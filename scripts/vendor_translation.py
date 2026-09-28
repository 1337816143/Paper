#!/usr/bin/env python3
"""Download ONLY an allowlisted Apache-licensed inference model and browser runtime.
No reader text, user annotations, credentials, or personal imports are sent anywhere.
Run on explicit preparation, not on ordinary static builds. No fonts are copied.
"""
from pathlib import Path
import json, hashlib, shutil, subprocess, urllib.request, time, re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'vendor/translation'
HF='https://huggingface.co'
MODEL='Xenova/opus-mt-en-zh'
FILES=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','special_tokens_map.json','onnx/encoder_model_quantized.onnx','onnx/decoder_model_merged_quantized.onnx']

def fetch(url,limit=95000000):
    last=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'PaperLab-local-reader/3.0'})
            with urllib.request.urlopen(req,timeout=120) as r:
                data=r.read(limit+1)
            if len(data)>limit:raise ValueError('Resource too large')
            return data
        except Exception as e:
            last=e;time.sleep(2*(attempt+1))
    raise last

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    staging=Path('/tmp/paper-translation-dependencies');staging.mkdir(exist_ok=True)
    subprocess.run(['npm','install','--prefix',str(staging),'--ignore-scripts','--no-audit','--no-fund','@huggingface/transformers@3.8.1'],check=True)
    tr=staging/'node_modules/@huggingface/transformers'
    lib=tr/'dist/transformers.web.min.js'
    if not lib.exists():raise FileNotFoundError('Reviewed browser entry missing: '+str(lib))
    shutil.copyfile(lib,OUT/'transformers.web.min.js')
    shutil.copyfile(tr/'LICENSE',OUT/'TRANSFORMERS-LICENSE')
    ort=staging/'node_modules/onnxruntime-web'; od=ort/'dist'
    wasm=OUT/'wasm';wasm.mkdir(exist_ok=True)
    for f in od.glob('ort-wasm-simd-threaded*'):
        if f.suffix in ['.mjs','.wasm'] and 'asyncify' not in f.name:
            shutil.copyfile(f,wasm/f.name)
    assert list(wasm.glob('*.wasm')) and list(wasm.glob('*.mjs'))
    if (ort/'LICENSE').exists():shutil.copyfile(ort/'LICENSE',OUT/'ONNXRUNTIME-LICENSE')
    md=json.loads(fetch(HF+'/api/models/'+MODEL));revision=md['sha'];assert re.fullmatch('[0-9a-f]{40}',revision)
    base=json.loads(fetch(HF+'/api/models/Helsinki-NLP/opus-mt-en-zh'))
    assert base.get('cardData',{}).get('license')=='apache-2.0','Model license changed; review required'
    target=OUT/'models/opus-mt-en-zh'
    for name in FILES:
        p=target/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(fetch(HF+'/'+MODEL+'/resolve/'+revision+'/'+name+'?download=true'))
    # Keep upstream cards and actual Apache text, not an assertion of an unknown license.
    (OUT/'MODEL-CARD.md').write_bytes(fetch(HF+'/'+MODEL+'/raw/'+revision+'/README.md'))
    (OUT/'BASE-MODEL-CARD.md').write_bytes(fetch(HF+'/Helsinki-NLP/opus-mt-en-zh/raw/'+base['sha']+'/README.md'))
    (OUT/'MODEL-LICENSE').write_bytes(fetch('https://www.apache.org/licenses/LICENSE-2.0.txt'))
    manifest={'schema':'paper.translation.assets.v1','model':MODEL,'revision':revision,'baseModel':'Helsinki-NLP/opus-mt-en-zh','baseRevision':base['sha'],'modelLicense':'Apache-2.0','runtime':'@huggingface/transformers@3.8.1','onnxRuntime':json.loads((ort/'package.json').read_text())['version'],'scope':'Browser-only private machine translation. No public translation of NoDerivatives originals. No remote inference.','files':[]}
    for p in sorted(OUT.rglob('*')):
        if p.is_file() and p.name!='manifest.json':
            assert p.suffix.lower() not in ['.ttf','.otf','.woff','.woff2']
            manifest['files'].append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    manifest['totalBytes']=sum(x['bytes'] for x in manifest['files'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'translationAssetBytes':manifest['totalBytes'],'modelRevision':revision,'files':len(manifest['files'])}))
if __name__=='__main__':main()
