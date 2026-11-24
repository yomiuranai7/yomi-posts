# よみ（星と数のこよみ）の Instagram・Threads 自動投稿

毎朝 日本時間 7:17 ごろに、その日の `posts/<日付>.json` を Instagram と Threads に投稿します（GitHub Actions）。
混んでいる日は数分〜数十分おくれることがあります。

## しくみ
- `posts/YYYY-MM-DD.json` … 1日1ファイル。`date`・`image`（docs/images の中の名前）・`ai_generated`（AI画像なら true）・`instagram`・`threads`
- `docs/images/` … 投稿の画像（JPEG・1080×1350）。GitHub Pages で公開し、Instagram・Threads がそのURLから取りに来ます
- `scripts/post.py` … 投稿する本体。`DRY_RUN` が `0` でなければ投稿せずに内容を表示するだけ
- `posted.log` … 投稿の記録（`日付 サービス ok 投稿ID`／DRY_RUN のときは `dry`）。`ok` がある日とサービスには二度投稿しません
- `.github/workflows/post.yml` … 毎朝の投稿（手動実行もできる。日付を入れるとその日のファイルを使う）
- `.github/workflows/refresh.yml` … 毎週月曜にトークンを更新して Secrets を上書き
- `make-images/make.py` … 投稿文と画像を作る（Mac 用）。`python3 make-images/make.py 最初の日 日数`
  - 日替わり：はじめまして → 今日のタロット → 今日のラッキー星座 → 数秘のひとこと → タロット…のくり返し。毎回「今日のラッキー（カラー・アイテム・フード）」つき
  - タロットは1910年の原画（パブリックドメイン）、星座は記号、よみは図形で描いた絵。AI画像はなし

**このリポジトリは公開です。入れた投稿文と画像は投稿前から誰でも見られます。入れた＝投稿してよい、の印です。**

## Secrets（Settings → Secrets and variables → Actions → Secrets）
| 名前 | 中身 |
|---|---|
| `IG_ACCESS_TOKEN` | Instagram のアクセストークン（Instagram ログイン版・60日有効のもの） |
| `THREADS_ACCESS_TOKEN` | Threads のアクセストークン（60日有効のもの） |
| `GH_PAT` | GitHub の fine-grained トークン（名前 yomi-posts・2027-11-23 まで）。対象はこのリポジトリだけ・権限は Contents・Secrets・Workflows の読み書き。トークン更新で Secrets を上書きするのに使う（Mac からファイルを送るときも同じトークン。Mac のキーチェーンに保存ずみ） |

トークンはファイルにもチャットにも書かず、ここに自分で貼ります。

## Variables（同じ画面の Variables）
| 名前 | 中身 |
|---|---|
| `DRY_RUN` | 置かない・または `1` のあいだは表示だけ。本番にするときに `0` にする |

## GitHub Pages
Settings → Pages → Source を「Deploy from a branch」、ブランチ `main`・フォルダ `/docs` にする。
画像のURLは `https://<ユーザー名>.github.io/<リポジトリ名>/images/<日付>.jpg` になります。

## 気をつけること
- トークンは60日で切れます。refresh.yml が毎週更新します。失敗したら Actions のメールが届くので、60日たつ前に作り直して Secrets に貼り直してください
- 公開リポジトリは60日動きがないと予約が止まります。毎朝の記録のコミットで動きが残ります
- AI で作った画像を使う日は `ai_generated` を `true` にします（Instagram は is_ai_generated、Threads は is_made_with_ai で申告）
- 同じ文を何度も投稿しない・人への自動返信やいいねはしない
