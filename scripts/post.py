"""今日（日本時間）の posts/<日付>.json を Instagram と Threads に投稿する。

環境変数
  DRY_RUN            1 なら投稿せずに送る内容だけ表示する（初期値 1）
  IG_ACCESS_TOKEN    Instagram のトークン（GitHub の Secrets から渡す）
  THREADS_ACCESS_TOKEN  Threads のトークン（同上）
  PAGES_BASE_URL     画像を置いている GitHub Pages のURL（例 https://<ユーザー名>.github.io/<リポジトリ名>/）
  POST_DATE          投稿する日をずらしたいとき（YYYY-MM-DD）。空なら今日

投稿ずみは posted.log に「日付 サービス ok 投稿ID」で残す。同じ日・同じサービスに二度は投稿しない。
トークンは表示もファイル保存もしない。標準ライブラリだけで動く。
"""
import json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, "posted.log")
JST = timezone(timedelta(hours=9))
IG = "https://graph.instagram.com"
TH = "https://graph.threads.net/v1.0"


def call(method, url, params):
    """API を呼ぶ。エラーのときはトークンを含めずに中身を表示して止める"""
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        raise SystemExit(f"API エラー {e.code} {url.split('?')[0]}: {body[:500]}")


def done_set():
    s = set()
    if os.path.exists(LOG):
        for line in open(LOG, encoding="utf-8"):
            p = line.split()
            if len(p) >= 3 and p[2] == "ok":
                s.add((p[0], p[1]))
    return s


def write_log(date, service, status, info=""):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{date} {service} {status} {info}".rstrip() + "\n")


def post_instagram(token, image_url, caption, ai):
    me = call("GET", f"{IG}/me", {"fields": "user_id,username", "access_token": token})
    uid = me.get("user_id") or me.get("id")
    params = {"image_url": image_url, "caption": caption, "access_token": token}
    if ai:
        params["is_ai_generated"] = "true"
    c = call("POST", f"{IG}/{uid}/media", params)["id"]
    for _ in range(20):  # 画像の取りこみが終わるまで待つ
        st = call("GET", f"{IG}/{c}", {"fields": "status_code", "access_token": token}).get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Instagram の画像の取りこみに失敗：{st}")
        time.sleep(5)
    return call("POST", f"{IG}/{uid}/media_publish", {"creation_id": c, "access_token": token})["id"]


def post_threads(token, image_url, text, ai):
    params = {"text": text, "access_token": token}
    if image_url:
        params.update(media_type="IMAGE", image_url=image_url)
    else:
        params["media_type"] = "TEXT"
    if ai:
        params["is_made_with_ai"] = "true"
    c = call("POST", f"{TH}/me/threads", params)["id"]
    time.sleep(30)  # 作ったものの準備ができるまで少し待つ
    return call("POST", f"{TH}/me/threads_publish", {"creation_id": c, "access_token": token})["id"]


def main():
    dry = os.environ.get("DRY_RUN", "1") != "0"
    date = os.environ.get("POST_DATE") or datetime.now(JST).strftime("%Y-%m-%d")
    path = os.path.join(ROOT, "posts", date + ".json")
    if not os.path.exists(path):
        print(f"{date} の投稿ファイルはありません。何もしません")
        return
    p = json.load(open(path, encoding="utf-8"))
    base = os.environ.get("PAGES_BASE_URL", "").rstrip("/") + "/"
    image_url = base + "images/" + p["image"] if p.get("image") else ""
    ai = bool(p.get("ai_generated"))
    done = done_set()

    if len(p.get("threads", "")) > 500:
        raise SystemExit("Threads の文が500字をこえています")
    if len(p.get("instagram", "")) > 2200:
        raise SystemExit("Instagram の文が2200字をこえています")

    print(f"=== {date}  DRY_RUN={'1' if dry else '0'}  画像={image_url or 'なし'}  AI画像={'はい' if ai else 'いいえ'}")
    for service, text in (("instagram", p.get("instagram")), ("threads", p.get("threads"))):
        if not text:
            continue
        if (date, service) in done:
            print(f"--- {service}：投稿ずみなのでとばします")
            continue
        print(f"--- {service}（{len(text)}字）\n{text}\n")
        if dry:
            write_log(date, service, "dry")
            continue
        if service == "instagram":
            tok = os.environ.get("IG_ACCESS_TOKEN")
            if not tok or not image_url:
                raise SystemExit("IG_ACCESS_TOKEN か画像がありません")
            pid = post_instagram(tok, image_url, text, ai)
        else:
            tok = os.environ.get("THREADS_ACCESS_TOKEN")
            if not tok:
                raise SystemExit("THREADS_ACCESS_TOKEN がありません")
            pid = post_threads(tok, image_url, text, ai)
        write_log(date, service, "ok", pid)
        print(f"投稿しました：{service} {pid}")


if __name__ == "__main__":
    main()
