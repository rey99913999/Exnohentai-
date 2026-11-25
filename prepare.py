import os, shutil, re
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
            # Normalize the old forum host after the general domain substitutions.
            s=s.replace("https://forums.ex.fangliding.eu.org","https://ex.fangliding.eu.org")
            s=s.replace('setOf("ex.fangliding.eu.org", "ex.fangliding.eu.org")','setOf("ex.fangliding.eu.org")')
            s=s.replace("import androidx.preference.EditTextPreference\n","")

            # This mirror uses one fixed host; remove E-Hentai account switching and login-cookie preferences.
            s=re.sub(r'    private val memberId: String by lazy \{ getMemberIdPref\(\) \}\n    private val passHash: String by lazy \{ getPassHashPref\(\) \}\n    private val igneous: String by lazy \{ getIgneousPref\(\) \}\n    private val forceEh: Boolean by lazy \{ getForceEhPref\(\) \}\n', '', s)
            s=re.sub(
                r'    // The site itself changes with the login state:.*?\n    // Listings are paged',
                '    override val baseUrl: String = "https://ex.fangliding.eu.org"\n\n    // Listings are paged',
                s, count=1, flags=re.S
            )
            s=re.sub(
                r'    private val cookieHeader by lazy \{.*?\n    \}\n\n    override fun OkHttpClient.Builder.configureClient',
                '    private val cookieHeader by lazy {\n'
                '        val excludedLanguages = languageMappings.filter { it.first != ehLang }\n'
                '            .flatMap { it.second }\n'
                '            .joinToString("x")\n'
                '        listOf("uconfig" to "prn_n-xl_$excludedLanguages", "nw" to "1")\n'
                '            .joinToString("; ") { "${it.first}=${it.second}" }\n'
                '    }\n\n'
                '    override fun OkHttpClient.Builder.configureClient',
                s, count=1, flags=re.S
            )
            s=re.sub(r'\n        private const val MEMBER_ID_PREF_KEY.*?\n        private const val FORCE_EH_DEFAULT_VALUE = true\n', '\n', s, count=1, flags=re.S)
            s=re.sub(r'        private val FORUMS_URL = .*?\n', '', s, count=1)
            s=re.sub(r'        val forceEhPref = CheckBoxPreference\(screen.context\)\.apply \{.*?\n        \}\n\n', '', s, count=1, flags=re.S)
            s=re.sub(r'        val memberIdPref = EditTextPreference\(screen.context\)\.apply \{.*?        val igneousPref = EditTextPreference\(screen.context\)\.apply \{.*?\n        \}\n\n', '', s, count=1, flags=re.S)
            s=s.replace('        screen.addPreference(forceEhPref)\n','')
            s=s.replace('        screen.addPreference(memberIdPref)\n','')
            s=s.replace('        screen.addPreference(passHashPref)\n','')
            s=s.replace('        screen.addPreference(igneousPref)\n','')
            s=re.sub(
                r'    private fun getCookieValue\(.*?\n    private fun getForceEhPref\(\): Boolean = preferences\.getBoolean\(FORCE_EH, FORCE_EH_DEFAULT_VALUE\)\n',
                '', s, count=1, flags=re.S
            )
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

# Rename the source file to match its transformed class name for ktlint.
old_file=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","exnohentai","EHentai.kt")
new_file=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","exnohentai","ExNoHentai.kt")
if os.path.isfile(old_file): shutil.move(old_file,new_file)
