# keiho-kaitori.com

株式会社KEIHO（催事買取）の公式サイト。GitHub Pages で配信しています。

- 本番: https://keiho-kaitori.com
- 配信: `main` への push で `.github/workflows/pages-deploy.yml` が自動デプロイ
- 独自ドメイン: `CNAME`（Pages を private リポジトリで配信するには有料プランが
  必要なため、**このリポジトリは public のまま**にしてください）

## 記事の追加方法

`blog/` または `news/` に Markdown ファイルを追加して push するだけです。
デプロイ時に `tools/build.py` が走り、記事ページ・一覧・sitemap.xml を生成します。

```
blog/2026-09-05-example.md
---
title: 記事タイトル
date: 2026-09-05
category: 買取知識
published: true
---

本文（Markdown）
```

`news/` は `category` の代わりに `type`（お知らせ／催事情報 など）を使います。
`published: false` にすると生成対象から外れます。

## ビルドが生成するもの

`tools/build.py` は次を出力します。手書きした HTML は上書きしません。

| 出力 | 内容 |
|---|---|
| `blog/<slug>/index.html` | 記事ページ（BlogPosting + BreadcrumbList） |
| `news/<slug>/index.html` | お知らせページ（NewsArticle + BreadcrumbList） |
| `blog/index.html` `news/index.html` | 一覧ページ（Blog / CollectionPage + ItemList） |
| `sitemap.xml` | 全URL（lastmod 付き） |
| `index.html` の一部 | `<!-- BUILD:NEWS_START -->` 〜 `_END`、`BUILD:BLOG_*` の間だけ差し替え |

**`index.html` を編集するときは BUILD マーカーの外側を触ってください。**
マーカーの内側はビルドごとに上書きされます。

## ローカルで確認する

```bash
python3 tools/build.py
python3 -m http.server 8791
# http://127.0.0.1:8791/
```

`/blog/` などのパスは絶対パス参照なので、`file://` ではなく HTTP で開いてください。

## 旧URLについて

`/blog/post.html?slug=xxx` は `/blog/xxx/` へ転送する互換ページです
（GitHub Pages は 301 を返せないため JS 転送 + canonical + noindex）。
既に貼られたリンクのために残しています。

## 公開されるもの / されないもの

GitHub Pages は `path: '.'` でリポジトリ全体を配信するため、**何もしないと
README や原稿の Markdown までURLで読めてしまう。** デプロイ時に
「Strip internal files from the artifact」ステップで下記を成果物から除外している。

| 除外 | 理由 |
|---|---|
| `README.md` | 社内向けの申し送り（本ファイル） |
| `tools/` | ビルドスクリプト。実行はCI側で完結する |
| `netlify.toml` | Netlify用。GitHub Pages では未使用 |
| `blog/*.md` `news/*.md` | 原稿。記事ページ生成後は不要。**`published: false` の下書きが読まれるのを防ぐ意味が大きい** |

`.github/` は GitHub Pages が元から配信しない。

**社内メモ・作業経緯・未確定事項は、配信されるファイル（`*.html` / `admin/config.yml`
/ `robots.txt` など）にコメントとして書かないこと。** 静的サイトなので
HTML・CSS・JS のコメントはすべてそのまま閲覧者に見える。書くならこの README か
コミットメッセージに残す。

## 未対応・注意点

- `admin/`（Decap CMS）は `backend: name: github` のみで OAuth プロバイダ未設定のため
  現状ログインできません。`netlify.toml` は Netlify Identity 前提の設定です。
- 催事スケジュール（`index.html` の `#saiji`）は「近日公開予定」のまま。
- 画像は `sips` で圧縮済み。差し替える際は長辺 480px 程度（アイコン）に抑えてください。
