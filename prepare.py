import os, shutil
src="upstream/src/all/ehentai"
dst="upstream/src/all/exnohentai"
if not os.path.isdir(src): raise SystemExit("Upstream E-Hentai module missing")
shutil.copytree(src,dst)
for root,dirs,files in os.walk(dst):
    for name in files:
        path=os.path.join(root,name)
        if name.endswith(".kt"):
            s=open(path,encoding="utf-8").read()
            s=s.replace("eu.kanade.tachiyomi.extension.all.ehentai","eu.kanade.tachiyomi.extension.all.exnohentai")
            s=s.replace("EHentai","ExNoHentai")
            s=s.replace("e-hentai.org","ex.fangliding.eu.org")
            s=s.replace("exhentai.org","ex.fangliding.eu.org")
            s=s.replace("https://forums.e-hentai.org","https://ex.fangliding.eu.org")
            open(path,"w",encoding="utf-8").write(s)
old=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","ehentai")
new=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","exnohentai")
if os.path.isdir(old): shutil.move(old,new)
gradle=os.path.join(dst,"build.gradle.kts")
s=open(gradle,encoding="utf-8").read()
s=s.replace('name = "E-Hentai"','name = "ExNoHentai"')
s=s.replace('baseUrl = "https://e-hentai.org"','baseUrl = "https://ex.fangliding.eu.org"')
s=s.replace('host("e-hentai.org")','host("ex.fangliding.eu.org")')
s=s.replace('host("exhentai.org")','host("ex.fangliding.eu.org")')
open(gradle,"w",encoding="utf-8").write(s)
print("Module copied and patched")
