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
            # Use the mirror's dedicated Popular page; the old search-parameter
            # approximation can return an empty or unrelated result set.
            s=re.sub(
                r'    override suspend fun getPopularManga\(page: Int\): MangasPage = if \(isLangNatural\(\)\) \{.*?\n    \}\n\n    override suspend fun getLatestUpdates',
                '    override suspend fun getPopularManga(page: Int): MangasPage = if (page == 1) {\n'
                '        loadListing("$baseUrl/popular", page)\n'
                '    } else {\n'
                '        MangasPage(emptyList(), false)\n'
                '    }\n\n'
                '    override suspend fun getLatestUpdates',
                s, count=1, flags=re.S
            )

            # Support all current E-Hentai listing layouts and distinguish an
            # actual empty result from a blocked/unrecognized HTML response.
            new_parser = """    private fun parseMangaPage(response: Response, listingUrl: String, page: Int, requestId: Long): ListingResult {
        val doc = response.asJsoup()
        val pageText = doc.body()?.text().orEmpty()
        val titleElements = doc.select(".itg .glink")

        val looksLikeCloudflare = response.header("cf-mitigated") == "challenge" ||
            doc.title().contains("Just a moment", ignoreCase = true) ||
            pageText.contains("Verify you are human", ignoreCase = true) ||
            pageText.contains("Checking your browser", ignoreCase = true) ||
            pageText.contains("Enable JavaScript and cookies to continue", ignoreCase = true)

        if (looksLikeCloudflare) {
            throw java.io.IOException(
                "Cloudflare verification page was returned. Open the mirror in Mihon's internal browser, complete verification, then retry."
            )
        }

        if (titleElements.isEmpty()) {
            val isRealEmptyResult = pageText.contains("No hits found", ignoreCase = true) ||
                pageText.contains("No results found", ignoreCase = true)
            if (isRealEmptyResult) return ListingResult(MangasPage(emptyList(), false), null)

            throw java.io.IOException(
                "ExNoHentai received an unrecognized listing page (HTTP ${response.code}, title='${doc.title()}'). " +
                    "Page text: ${pageText.take(160)}"
            )
        }

        val mangas = titleElements.mapNotNull { titleElement ->
            val link = titleElement.closest("a") ?: return@mapNotNull null
            val gallery = titleElement.closest("tr, .gl1t") ?: return@mapNotNull null
            val galleryTitle = titleElement.text().trim()
            val galleryUrl = link.attr("href")
            if (galleryTitle.isEmpty() || galleryUrl.isBlank()) return@mapNotNull null

            if (isLangNatural() && getEnforceLanguagePref()) {
                val language = gallery.selectFirst("[title^=language]")?.text()
                if (language != null && language != ehLang) return@mapNotNull null
            }

            SManga.create().apply {
                title = galleryTitle
                url = ExGalleryMetadata.normalizeUrl(galleryUrl)
                thumbnail_url = gallery.selectFirst(".glthumb img, .gl1e img, .gl3t img")?.let { img ->
                    img.absUrl("data-src").ifEmpty { img.absUrl("src") }.ifEmpty { null }
                }
            }
        }

        val lastGalleryHref = titleElements.lastOrNull()?.closest("a")?.attr("href")
        val nextId = doc.selectFirst("a#unext[href]")?.absUrl("href")?.toHttpUrlOrNull()?.queryParameter("next")
            ?: lastGalleryHref?.let { ExGalleryMetadata.galleryId(it) }

        nextId?.let { id ->
            val key = cursorKey(listingUrl, page + 1)
            synchronized(nextCursors) {
                val existing = nextCursors[key]
                if (existing == null || existing.requestId <= requestId) {
                    nextCursors[key] = Cursor(requestId, id)
                }
            }
        }

        val hasNextPage = doc.selectFirst("a#unext[href]")?.hasText() == true
        return ListingResult(MangasPage(mangas, hasNextPage), nextId)
    }"""
            s=re.sub(
                r'    private fun parseMangaPage\(response: Response, listingUrl: String, page: Int, requestId: Long\): ListingResult \{.*?\n    \}\n\n    // A gallery is a single chapter',
                lambda _: new_parser + "\n\n    // A gallery is a single chapter",
                s, count=1, flags=re.S
            )
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
            # Pull current mirror cookies from Mihon's shared jar on every request.
            # This allows a newly solved Cloudflare challenge to be used immediately.
            old_cookie_method = """    private fun proceedWithSiteCookies(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val host = baseUrl.toHttpUrl().host
        if (request.url.host != host && !request.url.host.endsWith(".$host")) return chain.proceed(request)
        return chain.proceed(request.newBuilder().header("Cookie", cookieHeader).build())
    }"""
            new_cookie_method = """    private fun proceedWithSiteCookies(chain: Interceptor.Chain): Response {
        val request = chain.request()
        val allowedHosts = setOf("ex.fangliding.eu.org", "e-hentai.org", "exhentai.org")
        if (request.url.host !in allowedHosts) return chain.proceed(request)

        // Source defaults are overridden by valid cookies from Mihon's shared jar.
        val cookies = linkedMapOf<String, String>()
        cookieHeader.split(";").forEach { entry ->
            val separator = entry.indexOf('=')
            if (separator > 0) {
                cookies[entry.substring(0, separator).trim()] =
                    entry.substring(separator + 1).trim()
            }
        }
        network.client.cookieJar.loadForRequest(request.url).forEach { cookie ->
            cookies[cookie.name] = cookie.value
        }

        val header = cookies.entries.joinToString("; ") { "${it.key}=${it.value}" }
        return if (header.isEmpty()) {
            chain.proceed(request)
        } else {
            chain.proceed(request.newBuilder().header("Cookie", header).build())
        }
    }"""
            if old_cookie_method in s:
                s = s.replace(old_cookie_method, new_cookie_method, 1)
                print("Applied Cloudflare cookie forwarding:", path)

            # Repair reader-page extraction for the mirror.
            # Keep pagination compatible with both the older onclick link and
            # the current E-Hentai pagination table (.ptds + td > a).
            old_page_list = """    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val pageUrls = mutableListOf<String>()
        var next: String? = "$baseUrl${chapter.url}"
        while (next != null) {
            val doc = client.get(next, Fetch.DOCUMENT).asJsoup()
            val hrefs = doc.select("#gdt a").map { it.attr("abs:href") }
            hrefs.firstOrNull { "/mpv/" in it }?.let { return getMpvPages(it) }
            pageUrls += hrefs
            next = nextPageUrl(doc)
        }
        return pageUrls.mapIndexed { index, url -> Page(index, url = url) }
    }"""
            new_page_list = """    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val pageUrls = mutableListOf<String>()
        var next: String? = "$baseUrl${chapter.url}"
        var pageNumber = 0
        var lastStatus = 0
        var lastFinalUrl = ""
        var lastTitle = ""
        var lastBodyText = ""
        var lastGdtCount = 0
        var lastImageLinks = 0
        var lastMpvLinks = 0
        var lastImageTags = 0
        while (next != null) {
            pageNumber++
            val response = client.get(next, Fetch.DOCUMENT)
            val doc = response.asJsoup()
            val pageText = doc.body()?.text().orEmpty()
            val challenge = response.header("cf-mitigated") == "challenge" ||
                doc.title().contains("Just a moment", ignoreCase = true) ||
                pageText.contains("Verify you are human", ignoreCase = true) ||
                pageText.contains("Checking your browser", ignoreCase = true)
            lastStatus = response.code
            lastFinalUrl = response.request.url.toString()
            lastTitle = doc.title()
            lastBodyText = pageText.take(350)
            lastGdtCount = doc.select("#gdt").size
            lastImageLinks = doc.select("#gdt a[href]").size
            lastMpvLinks = doc.select("a[href*=/mpv/]").size
            lastImageTags = doc.select("img").size

            if (!response.isSuccessful || challenge) {
                throw java.io.IOException(
                    "ExNoHentai chapter request failed: HTTP ${response.code}, " +
                        "requested=${next}, final=${response.request.url}, title='${doc.title()}'. " +
                        "Cloudflare challenge=${challenge}. Text=${pageText.take(180)}"
                )
            }

            val hrefs = doc.select("#gdt a[href]").map { it.absUrl("href") }.filter { it.isNotBlank() }
            hrefs.firstOrNull { "/mpv/" in it }?.let { return getMpvPages(it) }
            pageUrls += hrefs
            next = nextPageUrl(doc)
        }

        if (pageUrls.isEmpty()) {
            throw java.io.IOException(
                "ExNoHentai found no reader pages. Chapter=${chapter.url}, " +
                    "pageCount=0, lastRequest=${baseUrl}${chapter.url}, " +
                    "HTTP=${lastStatus}, final=${lastFinalUrl}, title='${lastTitle}'. " +
                    "BodyText=${lastBodyText}, gdtCount=${lastGdtCount}, " +
                    "imageLinks=${lastImageLinks}, mpvLinks=${lastMpvLinks}, " +
                    "imageTags=${lastImageTags}. Response did not contain usable reader links."
            )
        }

        return pageUrls.distinct().mapIndexed { index, url -> Page(index, url = url) }
    }"""
            if "override suspend fun getPageList(chapter: SChapter)" in s:
                s, reader_replacements = re.subn(
                    r'    override suspend fun getPageList\(chapter: SChapter\): List<Page> \{.*?\n    \}\n\n    private suspend fun getMpvPages',
                    lambda _: new_page_list + "\n\n    private suspend fun getMpvPages",
                    s, count=1, flags=re.S
                )
                if reader_replacements != 1:
                    raise SystemExit("Failed to apply reader page-list patch: " + path)
                print("Applied mirror reader extraction v3:", path)

            old_next_page = """    private fun nextPageUrl(element: Element) = element.select("a[onclick=return false]").last()?.let {
        if (it.text() == ">") it.attr("abs:href") else null
    }"""
            new_next_page = """    private fun nextPageUrl(element: Element): String? {
        val nextLink = element.selectFirst(".ptds + td a[href], .ptds+td>a[href], a#unext[href]")
            ?: element.select("a[onclick=return false]").lastOrNull()
                ?.takeIf { it.text().trim() == ">" }
        return nextLink?.absUrl("href")?.takeIf { it.isNotBlank() }
    }"""
            if old_next_page in s:
                s = s.replace(old_next_page, new_next_page, 1)
                print("Applied mirror reader pagination:", path)

            # Keep gallery deep links and image fallback strictly on the mirror host.
            s = s.replace(
                'if (url.host.removePrefix("www.") !in setOf("ex.fangliding.eu.org")) return null',
                'if (url.host != "ex.fangliding.eu.org") return null',
            )
            s = s.replace(
                'if (bakHttpUrl == null ||\n'
                '            !(bakHttpUrl.host == sourceHost || bakHttpUrl.host.endsWith(".$sourceHost"))\n'
                '        ) {',
                'if (bakHttpUrl == null || bakHttpUrl.host != sourceHost) {',
            )

            open(path,"w",encoding="utf-8").write(s)
old=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","ehentai")
new=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","exnohentai")
if os.path.isdir(old): shutil.move(old,new)
gradle=os.path.join(dst,"build.gradle.kts")
s=open(gradle,encoding="utf-8").read()
s=s.replace('name = "E-Hentai"','name = "ExNoHentai"')
s=re.sub(r"versionCode\s*=\s*\d+", "versionCode = 8", s, count=1)
s=s.replace('baseUrl = "https://e-hentai.org"','baseUrl = "https://ex.fangliding.eu.org"')
s=s.replace('host("e-hentai.org")','host("ex.fangliding.eu.org")')
s=s.replace('host("exhentai.org")','host("ex.fangliding.eu.org")')
open(gradle,"w",encoding="utf-8").write(s)
print("Module copied and patched")

# Rename the source file to match its transformed class name for ktlint.
old_file=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","exnohentai","EHentai.kt")
new_file=os.path.join(dst,"src","eu","kanade","tachiyomi","extension","all","exnohentai","ExNoHentai.kt")
if os.path.isfile(old_file): shutil.move(old_file,new_file)
