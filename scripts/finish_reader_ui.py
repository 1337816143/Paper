from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'src/app.js'
s=p.read_text()
s=s.replace('完整网站与练习ZIP','基础网站与练习ZIP')
s=s.replace('原文、原图及PDF在完整ZIP与完整缓存中','原文、原图及PDF在原文分卷与完整缓存中')
s=s.replace('<button data-action="export">学习笔记JSON</button></div><p><a href="#/offline-help">','<a class="btn secondary" href="downloads/index.html">下载全部原文分卷</a><button data-action="export">学习笔记JSON</button></div><p><a href="#/annotations">划线批注和便签备份</a> · <a href="#/offline-help">')
p.write_text(s)
p=ROOT/'content/navigation.json';items=json.loads(p.read_text())
for item in items:
 if item['id']=='offline-help':
  item['sections'][0][2]='先联网打开离线中心，点击完整缓存，等待正文、已归档原文、图表、原件和解析器全部下载后，再测试飞行模式刷新。完整原文库约224MB；未取得或无公开转载许可的资料可本机导入，不冒充已缓存。'
  item['sections'][1][2]='轻量单文件HTML只含带读与方法。完整原文使用网站完整缓存，或下载基础ZIP与全部原文分卷，解压到同一目录并运行python -m http.server。原文页提供PDF、EPUB和系统分享入口。外部阅读器不会自动同步本站批注。'
  item['sections'][3][2]='跨论文、概念和原文跳转保留阅读历史。划线、重点和便签在独立模块管理，可互相链接并跳回源段落。批注存在本机IndexedDB，旧整篇笔记与进度继续保留；两类备份各有导出按钮。'
p.write_text(json.dumps(items,ensure_ascii=False,indent=2)+'\n')
print('Offline download labels and help updated without clearing notes.')
