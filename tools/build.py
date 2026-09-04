#!/usr/bin/env python3
"""
静的サイトジェネレーター（SEO対応）

blog/*.md と news/*.md から、クロール可能な静的HTMLを生成します。

  blog/<slug>/index.html   記事ページ（BlogPosting 構造化データ）
  news/<slug>/index.html   お知らせページ（NewsArticle 構造化データ）
  blog/index.html          記事一覧
  news/index.html          お知らせ一覧
  sitemap.xml              全URL（lastmod付き）
  index.html               BUILD:*_START / _END マーカー間に一覧を差し込み

CMSやエディタで .md を追加 → push すると GitHub Actions が本スクリプトを
実行し、記事ページが自動生成されます。手書きしたHTMLはマーカー外なので
上書きされません。
"""
import os, re, html, json, datetime, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://keiho-kaitori.com"
SITE = "株式会社KEIHO"


# ---------- frontmatter ----------

def parse_md(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.S)
    if not m:
        return None, raw
    meta = {}
    for line in m.group(1).split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().strip('"').strip("'")
        meta[k.strip()] = {"true": True, "false": False}.get(v.lower(), v)
    return meta, m.group(2)


# ---------- markdown サブセット ----------

def md_inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)\)",
               r'<img src="\2" alt="\1" loading="lazy" decoding="async">', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def md_to_html(md):
    out, buf, lst = [], [], None

    def flush_p():
        if buf:
            out.append("<p>" + md_inline(" ".join(buf)) + "</p>")
            buf.clear()

    def flush_list():
        nonlocal lst
        if lst:
            tag = lst[0]
            out.append("<%s>%s</%s>" % (
                tag, "".join("<li>%s</li>" % md_inline(i) for i in lst[1]), tag))
            lst = None

    for line in md.split("\n"):
        s = line.rstrip()
        if not s.strip():
            flush_p(); flush_list(); continue
        h = re.match(r"^(#{1,4})\s+(.*)$", s)
        if h:
            flush_p(); flush_list()
            # 記事タイトルが h1 なので本文見出しは h2 から
            lvl = min(len(h.group(1)) + 1, 4)
            out.append("<h%d>%s</h%d>" % (lvl, md_inline(h.group(2)), lvl))
            continue
        b = re.match(r"^>\s?(.*)$", s)
        if b:
            flush_p(); flush_list()
            out.append("<blockquote><p>%s</p></blockquote>" % md_inline(b.group(1)))
            continue
        u = re.match(r"^[-*+]\s+(.*)$", s)
        o = re.match(r"^\d+[.)]\s+(.*)$", s)
        if u or o:
            flush_p()
            tag = "ul" if u else "ol"
            if not lst or lst[0] != tag:
                flush_list(); lst = (tag, [])
            lst[1].append((u or o).group(1))
            continue
        flush_list()
        buf.append(s.strip())
    flush_p(); flush_list()
    return "\n".join(out)


# ---------- 収集 ----------

def collect(folder, cat_key):
    items = []
    d = os.path.join(ROOT, folder)
    if not os.path.isdir(d):
        return items
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".md"):
            continue
        meta, body = parse_md(os.path.join(d, fn))
        if not meta or meta.get("published") is False:
            continue
        slug = fn[:-3]
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", md_to_html(body))).strip()
        items.append({
            "slug": slug,
            "title": str(meta.get("title") or slug),
            "date": str(meta.get("date") or slug[:10]),
            "cat": str(meta.get(cat_key) or ""),
            "thumb": meta.get("thumbnail") or "",
            "body": md_to_html(body),
            "excerpt": text[:110] + ("…" if len(text) > 110 else ""),
            "desc": text[:150],
            "url": "%s/%s/%s/" % (BASE, folder, slug),
            "path": "/%s/%s/" % (folder, slug),
        })
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def jp_date(d):
    try:
        y, m, dd = [int(x) for x in d[:10].split("-")]
        return "%d年%d月%d日" % (y, m, dd)
    except Exception:
        return d


# ---------- 共通テンプレート ----------

CSS = """
:root{--green:#1A5C3A;--green-dark:#0f3d27;--green-pale:#f0f7f3;--gold:#B8922A;
--gold-light:#d4aa50;--cream:#FAFAF6;--white:#fff;--text:#1c2a22;--text-mid:#4a5e52;
--text-light:#7a8f82;--border:#d4e3d9;}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Noto Sans JP',sans-serif;background:var(--cream);color:var(--text);}
header{background:rgba(255,255,255,.97);border-bottom:1px solid var(--border);padding:0 32px;
height:64px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.logo-link{display:flex;align-items:center;gap:12px;text-decoration:none;}
.logo-badge{width:40px;height:40px;background:var(--green);border-radius:9px;display:flex;
align-items:center;justify-content:center;}
.logo-badge span{font-family:'Shippori Mincho',serif;font-size:20px;font-weight:700;color:#fff;}
.logo-name{font-size:15px;font-weight:700;color:var(--green);}
.back-link{font-size:13px;color:var(--text-mid);text-decoration:none;display:flex;align-items:center;gap:6px;}
.back-link:hover{color:var(--green);}
.crumbs{max-width:900px;margin:0 auto;padding:18px 24px 0;font-size:12px;color:var(--text-light);}
.crumbs a{color:var(--text-mid);text-decoration:none;}
.crumbs a:hover{color:var(--green);}
.crumbs span{margin:0 6px;}
.article-wrap{max-width:760px;margin:24px auto 80px;padding:0 24px;}
.article-header{margin-bottom:32px;}
.article-meta{display:flex;align-items:center;gap:12px;margin-bottom:16px;}
.article-cat{font-size:11px;font-weight:700;color:var(--green);background:var(--green-pale);
padding:4px 12px;border-radius:100px;}
.article-date{font-size:12px;color:var(--text-light);}
.article-title{font-family:'Shippori Mincho',serif;font-size:clamp(22px,4vw,32px);font-weight:700;
color:var(--green-dark);line-height:1.5;margin-bottom:24px;}
.article-thumb{width:100%;border-radius:14px;margin-bottom:36px;}
.article-body{font-size:15px;line-height:2;color:var(--text-mid);}
.article-body h2{font-family:'Shippori Mincho',serif;font-size:22px;font-weight:700;
color:var(--green-dark);margin:40px 0 16px;padding-bottom:10px;border-bottom:2px solid var(--green-pale);}
.article-body h3{font-size:17px;font-weight:700;color:var(--green-dark);margin:28px 0 12px;}
.article-body p{margin-bottom:18px;}
.article-body ul,.article-body ol{padding-left:24px;margin-bottom:18px;}
.article-body li{margin-bottom:6px;}
.article-body img{max-width:100%;height:auto;border-radius:10px;margin:12px 0;}
.article-body a{color:var(--green);}
.article-body strong{color:var(--text);}
.article-body blockquote{border-left:3px solid var(--gold);padding:12px 20px;background:var(--green-pale);
border-radius:0 8px 8px 0;margin:20px 0;color:var(--text-mid);}
.cta{margin:56px 0 0;padding:28px 26px;background:var(--white);border:1.5px solid var(--border);border-radius:14px;}
.cta h2{font-family:'Shippori Mincho',serif;font-size:18px;color:var(--green-dark);margin-bottom:10px;
border:0;padding:0;}
.cta p{font-size:13.5px;color:var(--text-mid);line-height:1.9;margin-bottom:16px;}
.cta-row{display:flex;flex-wrap:wrap;gap:10px;}
.cta-row a{display:inline-flex;align-items:center;gap:7px;padding:12px 22px;border-radius:8px;
font-size:14px;font-weight:700;text-decoration:none;}
.cta-tel{background:var(--gold);color:#fff;}
.cta-form{background:var(--green);color:#fff;}
.back-btn{display:inline-flex;align-items:center;gap:8px;margin-top:40px;padding:12px 24px;
background:var(--green);color:#fff;border-radius:8px;font-size:14px;font-weight:700;text-decoration:none;}
.back-btn:hover{background:var(--green-dark);}
.list-wrap{max-width:900px;margin:24px auto 80px;padding:0 24px;}
.list-head{margin-bottom:36px;}
.list-tag{font-size:11px;font-weight:700;letter-spacing:.14em;color:var(--gold);margin-bottom:8px;}
.list-title{font-family:'Shippori Mincho',serif;font-size:clamp(24px,4.6vw,34px);font-weight:700;
color:var(--green-dark);margin-bottom:12px;}
.list-desc{font-size:14px;color:var(--text-mid);line-height:1.9;}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:20px;}
.card{background:var(--white);border:1.5px solid var(--border);border-radius:14px;overflow:hidden;
text-decoration:none;color:inherit;display:flex;flex-direction:column;transition:box-shadow .2s;}
.card:hover{box-shadow:0 6px 20px rgba(26,92,58,.1);}
.card-in{padding:20px 20px 22px;display:flex;flex-direction:column;gap:9px;flex:1;}
.card h2{font-size:15px;font-weight:700;color:var(--text);line-height:1.65;}
.card .ex{font-size:12.5px;color:var(--text-light);line-height:1.8;}
.rows{border-top:1px solid var(--border);}
.row{display:flex;gap:18px;align-items:baseline;padding:18px 4px;border-bottom:1px solid var(--border);
text-decoration:none;color:inherit;flex-wrap:wrap;}
.row:hover h2{color:var(--green);}
.row .d{font-size:12px;color:var(--text-light);white-space:nowrap;}
.row h2{font-size:14.5px;font-weight:700;line-height:1.7;flex:1;min-width:200px;}
footer{background:var(--green-dark);color:rgba(255,255,255,.72);padding:36px 24px;font-size:12px;
text-align:center;line-height:2;}
footer a{color:rgba(255,255,255,.9);}
@media(max-width:640px){header{padding:0 18px;}.logo-name{font-size:13px;}}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
         '<link href="https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@500;700'
         '&family=Noto+Sans+JP:wght@400;500;700&display=swap" rel="stylesheet">')

GA = """<script async src="https://www.googletagmanager.com/gtag/js?id=G-6TB53B0DQK"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}
gtag('js',new Date());gtag('config','G-6TB53B0DQK');</script>"""

FOOTER = ("""<footer>
<p>株式会社KEIHO ｜ 〒344-0057 埼玉県春日部市備後西3丁目6番46号 102 ｜ TEL <a href="tel:09057037929">090-5703-7929</a></p>
<p>古物商許可証：埼玉県公安委員会　第431260070630号</p>
<p><a href="/">トップ</a> ｜ <a href="/news/">新着情報</a> ｜ <a href="/blog/">ブログ</a> ｜ <a href="/privacy.html">プライバシーポリシー</a> ｜ <a href="/antisocial.html">反社排除・免責事項</a></p>
<p>Copyright &copy; 2026 株式会社KEIHO All Rights Reserved.</p>
</footer>""")

HEADER = """<header>
<a href="/" class="logo-link"><div class="logo-badge"><span>K</span></div>
<span class="logo-name">株式会社KEIHO</span></a>
<a href="%s" class="back-link">
<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
%s</a></header>"""

CTA = """<div class="cta">
<h2>金・プラチナ・宝飾品の買取はKEIHOへ</h2>
<p>査定は無料・予約不要です。関東を中心に全国の催事会場で開催しています。金額にご納得いただけない場合はお断りいただいて構いません。</p>
<div class="cta-row"><a href="tel:09057037929" class="cta-tel">090-5703-7929</a>
<a href="/#contact" class="cta-form">フォームで相談する</a></div>
</div>"""


def page(title, desc, canon, body, ld, og_type="website", image=None):
    e = lambda t: html.escape(str(t), quote=True)
    img = image or BASE + "/images/ogp.jpg"
    if img.startswith("/"):
        img = BASE + img
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<meta name="theme-color" content="#1A5C3A">
<link rel="canonical" href="{e(canon)}">
<link rel="icon" type="image/png" href="/images/favicon.png">
<link rel="apple-touch-icon" sizes="180x180" href="/images/favicon.png">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(canon)}">
<meta property="og:type" content="{og_type}">
<meta property="og:image" content="{e(img)}">
<meta property="og:site_name" content="{SITE}">
<meta property="og:locale" content="ja_JP">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{e(img)}">
{FONTS}
{GA}
<style>{CSS}</style>
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
</head>
<body>
{body}
{FOOTER}
</body>
</html>
"""


def crumbs(trail):
    """trail: [(名前, パス or None)] — 最後の要素は現在ページ"""
    parts, ld = [], []
    for i, (name, path) in enumerate(trail):
        ld.append({"@type": "ListItem", "position": i + 1, "name": name,
                   **({"item": BASE + path} if path else {})})
        parts.append(f'<a href="{path}">{html.escape(name)}</a>' if path
                     else f"<span aria-current=\"page\">{html.escape(name)}</span>")
    nav = ('<nav class="crumbs" aria-label="パンくずリスト">'
           + '<span>›</span>'.join(parts) + "</nav>")
    return nav, {"@type": "BreadcrumbList", "itemListElement": ld}


ORG = {"@type": "Organization", "@id": BASE + "/#organization", "name": SITE,
       "url": BASE + "/",
       "logo": {"@type": "ImageObject", "url": BASE + "/images/logo.png",
                "width": 132, "height": 132}}


# ---------- 記事ページ ----------

def write_article(it, kind):
    folder = "blog" if kind == "blog" else "news"
    label = "ブログ" if kind == "blog" else "新着情報"
    art_type = "BlogPosting" if kind == "blog" else "NewsArticle"
    nav, bc = crumbs([("ホーム", "/"), (label, f"/{folder}/"), (it["title"], None)])

    thumb = (f'<img class="article-thumb" src="{html.escape(it["thumb"])}" '
             f'alt="{html.escape(it["title"])}" loading="lazy" decoding="async">'
             if it["thumb"] else "")
    cat = f'<span class="article-cat">{html.escape(it["cat"])}</span>' if it["cat"] else ""

    body = f"""{HEADER % (f'/{folder}/', label + '一覧へ')}
{nav}
<article class="article-wrap">
<div class="article-header">
<div class="article-meta">{cat}<time class="article-date" datetime="{it['date'][:10]}">{jp_date(it['date'])}</time></div>
<h1 class="article-title">{html.escape(it['title'])}</h1>
</div>
{thumb}
<div class="article-body">
{it['body']}
</div>
{CTA}
<a href="/{folder}/" class="back-btn">{label}一覧へ戻る</a>
</article>"""

    ld = {"@context": "https://schema.org", "@graph": [ORG, bc, {
        "@type": art_type, "@id": it["url"] + "#article",
        "headline": it["title"], "name": it["title"],
        "description": it["desc"], "inLanguage": "ja",
        "datePublished": it["date"][:10], "dateModified": it["date"][:10],
        "mainEntityOfPage": {"@type": "WebPage", "@id": it["url"]},
        "author": {"@id": BASE + "/#organization"},
        "publisher": {"@id": BASE + "/#organization"},
        "image": it["thumb"] or BASE + "/images/ogp.jpg",
        **({"articleSection": it["cat"]} if it["cat"] else {}),
    }]}

    d = os.path.join(ROOT, folder, it["slug"])
    os.makedirs(d, exist_ok=True)
    open(os.path.join(d, "index.html"), "w", encoding="utf-8").write(
        page(f"{it['title']}｜{SITE}", it["desc"], it["url"], body, ld, "article",
             image=it["thumb"] or None))


# ---------- 一覧ページ ----------

def write_index(items, kind):
    folder = "blog" if kind == "blog" else "news"
    if kind == "blog":
        label, tag, title = "ブログ", "Blog", f"ブログ｜{SITE}"
        desc = ("株式会社KEIHOのブログ。金・プラチナ・宝飾品・時計の買取知識や"
                "査定のポイント、催事買取に関する情報を発信しています。")
        lead = "買取の知識や査定のポイント、催事買取に関する情報をお届けします。"
    else:
        label, tag, title = "新着情報", "News", f"新着情報・催事情報｜{SITE}"
        desc = ("株式会社KEIHOの新着情報。催事買取の開催予定・お知らせを掲載しています。"
                "関東中心に全国の商業施設で開催中。")
        lead = "催事買取の開催予定やお知らせを掲載しています。"

    nav, bc = crumbs([("ホーム", "/"), (label, None)])

    if kind == "blog":
        cards = "\n".join(
            f'<a class="card" href="{it["path"]}"><div class="card-in">'
            f'<div class="article-meta" style="margin:0;">'
            + (f'<span class="article-cat">{html.escape(it["cat"])}</span>' if it["cat"] else "")
            + f'<time class="article-date" datetime="{it["date"][:10]}">{jp_date(it["date"])}</time></div>'
              f'<h2>{html.escape(it["title"])}</h2>'
              f'<p class="ex">{html.escape(it["excerpt"])}</p>'
              f"</div></a>" for it in items)
        listing = f'<div class="cards">{cards}</div>' if items else \
            '<p class="list-desc">まだ記事がありません。</p>'
    else:
        rows = "\n".join(
            f'<a class="row" href="{it["path"]}">'
            f'<time class="d" datetime="{it["date"][:10]}">{jp_date(it["date"])}</time>'
            + (f'<span class="article-cat">{html.escape(it["cat"])}</span>' if it["cat"] else "")
            + f'<h2>{html.escape(it["title"])}</h2></a>' for it in items)
        listing = f'<div class="rows">{rows}</div>' if items else \
            '<p class="list-desc">まだお知らせがありません。</p>'

    body = f"""{HEADER % ('/', 'トップへ')}
{nav}
<main class="list-wrap">
<div class="list-head">
<div class="list-tag">{tag}</div>
<h1 class="list-title">{label}</h1>
<p class="list-desc">{lead}</p>
</div>
{listing}
{CTA}
</main>"""

    ld = {"@context": "https://schema.org", "@graph": [ORG, bc, {
        "@type": "Blog" if kind == "blog" else "CollectionPage",
        "@id": f"{BASE}/{folder}/#listing",
        "name": label, "description": desc, "url": f"{BASE}/{folder}/",
        "inLanguage": "ja", "publisher": {"@id": BASE + "/#organization"},
        "mainEntity": {"@type": "ItemList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": it["url"], "name": it["title"]}
            for i, it in enumerate(items)]},
    }]}

    open(os.path.join(ROOT, folder, "index.html"), "w", encoding="utf-8").write(
        page(title, desc, f"{BASE}/{folder}/", body, ld))


# ---------- index.html への差し込み ----------

def inject(news, blog):
    p = os.path.join(ROOT, "index.html")
    s = open(p, encoding="utf-8").read()

    if news:
        n = "\n".join(
            f'<a href="{it["path"]}" style="display:flex;gap:18px;align-items:baseline;padding:18px 4px;'
            f'border-bottom:1px solid var(--border);text-decoration:none;color:inherit;flex-wrap:wrap;">'
            f'<time datetime="{it["date"][:10]}" style="font-size:12px;color:var(--text-light);'
            f'white-space:nowrap;">{jp_date(it["date"])}</time>'
            + (f'<span style="font-size:11px;font-weight:700;color:var(--green);'
               f'background:var(--green-soft);padding:3px 11px;border-radius:100px;">'
               f'{html.escape(it["cat"])}</span>' if it["cat"] else "")
            + f'<span style="font-size:14.5px;font-weight:700;line-height:1.7;flex:1;min-width:200px;">'
              f'{html.escape(it["title"])}</span></a>' for it in news[:5])
    else:
        n = ('<div style="padding:24px 0;text-align:center;color:var(--text-light);'
             'font-size:13px;">まだお知らせがありません</div>')

    if blog:
        b = "\n".join(
            f'<a href="{it["path"]}" style="background:var(--white);border:1.5px solid var(--border);'
            f'border-radius:14px;overflow:hidden;text-decoration:none;color:inherit;display:block;">'
            f'<div style="padding:20px 20px 22px;">'
            f'<div style="font-size:11px;color:var(--text-light);margin-bottom:10px;">'
            f'{jp_date(it["date"])}'
            + (f'　&middot;　{html.escape(it["cat"])}' if it["cat"] else "")
            + f'</div><div style="font-size:14.5px;font-weight:700;color:var(--text);'
              f'line-height:1.65;margin-bottom:9px;">{html.escape(it["title"])}</div>'
              f'<div style="font-size:12.5px;color:var(--text-light);line-height:1.8;">'
              f'{html.escape(it["excerpt"])}</div></div></a>' for it in blog[:6])
    else:
        b = ('<div style="grid-column:1/-1;padding:24px 0;text-align:center;'
             'color:var(--text-light);font-size:13px;">まだ記事がありません</div>')

    for key, val in (("NEWS", n), ("BLOG", b)):
        pat = re.compile(r"(<!-- BUILD:%s_START -->).*?(<!-- BUILD:%s_END -->)" % (key, key), re.S)
        if not pat.search(s):
            sys.exit("index.html: BUILD:%s マーカーが見つかりません" % key)
        s = pat.sub(lambda m: m.group(1) + "\n" + val + "\n" + m.group(2), s, count=1)

    open(p, "w", encoding="utf-8").write(s)


# ---------- sitemap ----------

def write_sitemap(news, blog):
    today = datetime.date.today().isoformat()
    def mtime(rel):
        try:
            return datetime.date.fromtimestamp(
                os.path.getmtime(os.path.join(ROOT, rel))).isoformat()
        except OSError:
            return today

    urls = [(BASE + "/", mtime("index.html"), "weekly", "1.0"),
            (BASE + "/blog/", max([i["date"][:10] for i in blog] or [today]), "weekly", "0.7"),
            (BASE + "/news/", max([i["date"][:10] for i in news] or [today]), "weekly", "0.7")]
    urls += [(i["url"], i["date"][:10], "monthly", "0.6") for i in blog]
    urls += [(i["url"], i["date"][:10], "monthly", "0.6") for i in news]
    urls += [(BASE + "/privacy.html", mtime("privacy.html"), "yearly", "0.3"),
             (BASE + "/antisocial.html", mtime("antisocial.html"), "yearly", "0.3")]

    body = "\n".join(
        "  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n"
        "    <changefreq>%s</changefreq>\n    <priority>%s</priority>\n  </url>" % u
        for u in urls)
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + body + "\n</urlset>\n")
    return len(urls)


def main():
    blog = collect("blog", "category")
    news = collect("news", "type")
    for it in blog:
        write_article(it, "blog")
    for it in news:
        write_article(it, "news")
    write_index(blog, "blog")
    write_index(news, "news")
    inject(news, blog)
    n = write_sitemap(news, blog)
    print("build: blog %d 件 / news %d 件 / sitemap %d URL" % (len(blog), len(news), n))


if __name__ == "__main__":
    main()
