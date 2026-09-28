from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'src/study.js';s=p.read_text();s=s.replace("addEventListener('resize',hideTerm);addEventListener('scroll',hideTerm,{passive:true});", "addEventListener('resize',hideTerm);addEventListener('wheel',hideTerm,{passive:true});addEventListener('touchmove',hideTerm,{passive:true});")
p.write_text(s)
print('Popover remains open after automatic scroll; outside tap, Escape and deliberate scrolling close it.')
