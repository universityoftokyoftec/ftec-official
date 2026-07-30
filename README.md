# 東京大学 F-tec 公式サイト（静的移植版）

ChatGPT Sitesで公開されていたF-tec公式サイトを、GitHub Pages／Vercelで運用できる静的HTMLとして整理したものです。

## 含まれるページ

- `/` トップページ
- `/about/` F-tecについて
- `/about/teams/` 班紹介
- `/join/` 入会案内
- `/aircraft/tansei-zero/` たんせい零號
- `/aircraft/archive/` 過年度機体
- `/activity/` 活動記録
- `/gallery/production/` TFの風景
- `/gallery/workshop/` 作業場の風景
- `/sponsors/` 協賛・ご支援
- `/contact/` お問い合わせ

## 最も簡単な公開方法：Vercel

1. このフォルダの中身をGitHubの新しいリポジトリへアップロードします。
2. Vercelで `Add New → Project` を開き、GitHubリポジトリを選択します。
3. Framework Presetは `Other` のまま、Build CommandとOutput Directoryは空欄でDeployします。
4. 独自ドメインを使う場合は、Vercelの `Settings → Domains` から設定します。

## GitHub Pagesで公開する場合

1. リポジトリの `Settings → Pages` を開きます。
2. `Deploy from a branch` を選択します。
3. Branchを `main`、Folderを `/(root)` に設定します。

内部リンクは相対パスにしているため、`ユーザー名.github.io/リポジトリ名/` 配下でも動作します。

## 問い合わせフォーム

現在はサーバー不要の方式として、送信ボタンから利用者のメールアプリを開き、F-tecのメールアドレス宛てに入力内容を引き継ぎます。Web上で直接送信完了させたい場合は、Formspree、Google Apps Script、Vercel Functionsなどへの接続が必要です。

## 注意事項

- 画像とCSSは各HTML内に埋め込まれているため、見た目の再現性は高い一方、リポジトリ容量は大きめです。
- ChatGPT Sites固有の編集機能は含まれません。
- 公開後は、各ページのHTMLを直接編集して更新します。
- 将来的には共通CSS・画像・ヘッダーを分離すると、更新しやすく容量も小さくできます。
