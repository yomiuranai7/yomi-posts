"""投稿（posts/*.json）と画像（docs/images/*.jpg）と、確認用の一覧（../posts-review.md）を作る。
使い方：python3 make-images/make.py [最初の日 YYYY-MM-DD] [日数]（省略すると 2026-12-01 から7日分）

日替わりの順番：1日目は「はじめまして」。そのあとは
  今日のタロット → 今日のラッキー星座 → 数秘のひとこと（1・2・3…と進む）をくり返す
文のもとはサイトの文（app/js/texts.js・texts-tarot.js。このプロジェクトで書いた文）と、このファイルに書いた雰囲気の一言。
カードと星座は日付から決まる（同じ日付なら何度作っても同じ）。タロットは22回・星座は12回続けて出しても重ならない。
画像：よみは sns/x-icon.png（図形で描いたもの）、タロットは app/img/tarot（1910年の原画・パブリックドメイン）。どちらもAI画像ではない。
Mac の Google Chrome と node で作る。"""
import json, os, random, subprocess, sys, shutil
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
FORTUNE = os.path.normpath(os.path.join(REPO, "..", ".."))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SITE = "https://hoshitokazu-koyomi.pages.dev/"
EPOCH = date(2026, 1, 1)  # カードと星座の順番を決める起点

TAGS = {
    "intro": "#占い #数秘術 #タロット #星座占い #星と数のこよみ",
    "tarot": "#タロット #今日のタロット #タロット占い #占い #星と数のこよみ",
    "star": "#星座占い #今日の運勢 #12星座 #占い #星と数のこよみ",
    "num": "#占い #数秘術 #ライフパスナンバー #今日のひとこと #星と数のこよみ",
}

# ---- 雰囲気の一言（日付ごとに順番に使う） ----
TAROT_OPEN = [
    "おはようございます。\n今朝もカードを1枚めくりました。",
    "おはようございます。\n夜明けの静けさの中でカードを1枚引きました。",
    "おはようございます。\nまだ少し星の残る空の下でカードをめくりました。",
    "おはようございます。\n深呼吸をひとつしてからカードを引きました。",
]
TAROT_CLOSE = [
    "今日のあなたの一日がおだやかに流れますように。",
    "カードの言葉をポケットに入れて出かけてみてくださいね。",
    "夜にこのカードを思い出したら……今日のあなたを少しほめてあげてください。",
    "あなたの今日に小さな灯りがともりますように。",
]
STAR_OPEN = [
    "おはようございます。\n今日の星をのぞいてみました。",
    "おはようございます。\n夜空の名残りをたどって今日の星座を選びました。",
    "おはようございます。\n今日いちばん光って見えた星座のお話です。",
]
# 今日のラッキー（日付で順番に。長さをずらして組み合わせが毎日変わるようにしている）
COLORS = ["ラベンダー", "ミントグリーン", "夜空のネイビー", "ミルクティーベージュ", "さくらピンク", "金色", "空色",
          "クリーム色", "ボルドー", "オリーブグリーン", "白", "ターコイズ", "オレンジ", "シルバー"]
ITEMS = ["手帳", "ハンカチ", "お気に入りのペン", "手鏡", "腕時計", "ハンドクリーム", "しおり", "マグカップ",
         "イヤホン", "キーホルダー", "ポーチ", "小さなノート", "ヘアクリップ"]
FOODS = ["いちご", "あたたかいスープ", "はちみつ", "おにぎり", "チョコレート", "みかん", "焼きいも", "ハーブティー",
         "たまご料理", "焼きたてのパン", "抹茶", "ヨーグルト", "ナッツ", "りんご", "お味噌汁", "クッキー", "バナナ"]


def lucky(d):
    n = (d - EPOCH).days
    return COLORS[n % len(COLORS)], ITEMS[n % len(ITEMS)], FOODS[n % len(FOODS)]

# 12星座ごとの「今日のおすすめ」（ここで書いた文）
STAR_ACT = {
    "aries": "朝いちばんに今日やることを1つ決めて動き出してみてくださいね。",
    "taurus": "お気に入りの飲みものをゆっくり味わう時間を作ってみてくださいね。",
    "gemini": "しばらく話していない人に短いメッセージを送ってみてくださいね。",
    "cancer": "帰る場所を少し整えて自分をねぎらってみてくださいね。",
    "leo": "今日がんばったことを自分でほめてあげてくださいね。",
    "virgo": "気になっていた小さな場所を1つだけ整えてみてくださいね。",
    "libra": "目に入る場所に好きな色や花を1つ置いてみてくださいね。",
    "scorpio": "ひとつのことにじっくり向き合う時間を作ってみてくださいね。",
    "sagittarius": "いつもと違う本や場所にふれてみてくださいね。",
    "capricorn": "今日の小さな「できた」をメモに残してみてくださいね。",
    "aquarius": "思いついたアイデアを誰かに話してみてくださいね。",
    "pisces": "好きな音楽を聴きながら心をほどく時間を作ってみてくださいね。",
}
SIGN_ORDER = list(STAR_ACT)
SIGN_MARK = dict(zip(SIGN_ORDER, "♈♉♊♋♌♍♎♏♐♑♒♓"))

# 数秘のひとこと：今日できること（ここで書いた文）
NUM_ACT = {
    1: "気になっていたことを1つだけ始めてみてくださいね。",
    2: "身近な人に「ありがとう」をひとつ伝えてみてくださいね。",
    3: "好きなものの話をする時間を作ってみてくださいね。",
    4: "机の上を1か所だけ整えてみてくださいね。",
    5: "いつもと違う道を通ってみてくださいね。",
    6: "人のためだけでなく自分にもやさしくする時間を作ってみてくださいね。",
    7: "ひとりで静かに考える時間を少しだけ作ってみてくださいね。",
    8: "今週の目標をひとつ数字で書いてみてくださいね。",
    9: "使わなくなったものを1つ手放してみてくださいね。",
    11: "ふと浮かんだ気づきをメモに残してみてくださいね。",
    22: "大きな夢を今日の小さな作業に分けてみてくださいね。",
    33: "誰かに向けるやさしさを今日は自分にも向けてみてくださいね。",
}
NUM_ORDER = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33]
HOWTO = ("ライフパス数は生年月日から出します。\n"
         "生年月日の数字を全部たして1けたになるまでたすんです。\n"
         "11・22・33になったときはそのまま残します。")


def site_texts():
    js = os.path.join(FORTUNE, "app", "js")
    code = ("const T=require('./texts.js'),R=require('./texts-tarot.js');"
            "const c={0:R.FOOL.card};for(let i=1;i<=21;i++)c[i]=T.CARDS[i];"
            "const up={};for(let i=0;i<=21;i++)up[i]=R.SPREAD[i].up;"
            "console.log(JSON.stringify({cards:c,up:up,signs:T.SIGNS,nums:T.NUMBERS}))")
    out = subprocess.run(["node", "-e", code], cwd=js, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def cyclic(items, d, salt):
    """日付から順番に選ぶ。同じ種類は3日に1回なので3日ごとに1つ進む。
    並びは一度だけシャッフルして固定（どこから数えても、続けて出る22枚・12星座は重ならない）"""
    n = (d - EPOCH).days // 3
    order = list(items)
    random.Random(salt).shuffle(order)
    return order[n % len(order)]


def pick(lst, d):
    return lst[(d - EPOCH).days % len(lst)]


def tarot_post(t, d):
    n = cyclic(range(22), d, "tarot")
    c = t["cards"][str(n)]
    up = t["up"][str(n)]
    msg = "" if c["msg"][:4] in up else f"「{c['msg']}」\n"  # 同じ言葉が続くときは入れない
    body = (f"{pick(TAROT_OPEN, d)}\n\n今日のタロットは……「{c['name']}」です。\n\n"
            f"キーワードは「{c['key']}」。\n{up}\n\n{msg}{pick(TAROT_CLOSE, d)}")
    img = dict(kind="tarot", card=n, sub="今日のタロット", a=c["name"], b=f"「{c['key']}」")
    return "tarot", body, img


def star_post(t, d):
    k = cyclic(SIGN_ORDER, d, "star")
    s = t["signs"][k]
    body = (f"{pick(STAR_OPEN, d)}\n\n今日のラッキー星座は……{s['name']}です。\n\n"
            f"{s['name']}は「{s['role']}」。\n{s['free']}\n"
            f"今日はその持ち味がのびのび出やすい日と出ています。\n\n"
            f"{s['name']}の人は{STAR_ACT[k]}\n\n"
            f"ほかの星座の人も少しまねしてみると今日がやさしく進みそうです。")
    img = dict(kind="star", mark=SIGN_MARK[k], sub="今日のラッキー星座", a=s["name"], b=f"「{s['role']}」")
    return "star", body, img


def num_post(t, n, first):
    w = t["nums"][str(n)]
    body = (f"数秘で「{n}」を持つ人へ。今日のひとことです。\n\n"
            f"「{n}」のキーワードは「{w['word']}」。\n{w['life']}\n\n"
            f"周りからは「{w['first']}」と見られやすいんです。\n"
            f"でも心の中では「{w['inner']}」と思っていませんか？\n\n"
            f"今日は{NUM_ACT[n]}")
    if first:
        body = HOWTO + "\n\n" + body
    img = dict(kind="yomi", sub="今日のひとこと", a=f"数秘「{n}」の人へ", b=f"キーワードは「{w['word']}」")
    return "num", body, img


def build(start, days):
    t = site_texts()
    out = []
    intro = ("はじめまして。「星と数のこよみ」の案内役のよみです。\n\n"
             "誕生日と名前からあなたの本質とこれからを読んでいます。\n"
             "使うのは12星座・四柱推命・カバラ数秘・タロット・間取り風水の5つです。\n\n"
             "ここでは毎朝ひとつ占いを置いていきますね。\n"
             "今日のタロット・今日のラッキー星座・数秘のひとことを日替わりでお届けします。")
    out.append(("intro", intro, dict(kind="yomi", sub="誕生日と名前から読む占い", a="はじめまして", b="案内役のよみです")))
    num_i = 0
    for i in range(1, days):
        d = start + timedelta(days=i)
        kind = ("tarot", "star", "num")[(i - 1) % 3]
        if kind == "tarot":
            k, body, img = tarot_post(t, d)
        elif kind == "star":
            k, body, img = star_post(t, d)
        else:
            n = NUM_ORDER[num_i % len(NUM_ORDER)]
            k, body, img = num_post(t, n, first=num_i == 0)
            num_i += 1
        col, item, food = lucky(d)
        body += f"\n\n今日のラッキー\nカラー：{col}\nアイテム：{item}\nフード：{food}"
        img["lucky"] = (col, item, food)
        out.append((k, body, img))
    posts = []
    for i, (kind, body, img) in enumerate(out):
        link = i % 3 == 0  # 3投稿に1回だけ無料占いへの案内
        ig, th = body, body
        if link:
            ig += "\n\nあなたの星座や数は無料の占いでわかります。プロフィールのリンクからどうぞ。"
            th += f"\n\nあなたの星座や数は無料の占いでわかります。\n{SITE}"
        ig += "\n\n" + TAGS[kind]
        posts.append((kind, ig, th, img))
    return posts


PAGE = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;width:1080px;height:1350px;overflow:hidden}}
body{{background:radial-gradient(ellipse at 50% 38%,#3b2f86 0%,#1b1546 55%,#0b0922 100%);
font-family:"Hiragino Mincho ProN","Yu Mincho",serif;color:#f6e7b8;text-align:center;position:relative}}
.st{{position:absolute;border-radius:50%;background:#fff}}
.icon{{position:absolute;left:340px;top:150px;width:400px;height:400px;border-radius:50%;box-shadow:0 0 80px rgba(143,123,255,.5)}}
.card{{position:absolute;left:390px;top:70px;width:300px;height:503px;border-radius:14px;border:3px solid #e9c66c;box-shadow:0 0 70px rgba(143,123,255,.55)}}
.mark{{position:absolute;left:340px;top:150px;width:400px;height:400px;border-radius:50%;border:3px solid #e9c66c;
box-shadow:0 0 80px rgba(143,123,255,.5),inset 0 0 60px rgba(143,123,255,.35);font-family:"Apple Symbols","Hiragino Mincho ProN";
font-size:230px;line-height:400px;color:#f3d88a;box-sizing:border-box}}
.sub{{position:absolute;top:640px;width:100%;font-size:44px;letter-spacing:.2em;color:#cfc6ff}}
.big{{position:absolute;top:720px;width:100%;font-size:{size}px;font-weight:600;color:#f3d88a;text-shadow:0 4px 20px rgba(0,0,0,.4)}}
.mid{{position:absolute;top:900px;width:100%;font-size:64px;color:#fff3c8}}
.line{{position:absolute;top:1040px;left:340px;width:400px;height:2px;background:linear-gradient(90deg,transparent,#e9c66c,transparent)}}
.lk{{position:absolute;top:1062px;width:100%;font-size:32px;line-height:1.6;color:#e8e0ff;letter-spacing:.05em}}
.lk b{{color:#e9c66c;font-weight:600;margin-right:.5em}}
.foot{{position:absolute;bottom:90px;width:100%;font-size:40px;letter-spacing:.15em;color:#e9c66c}}
</style></head><body>{stars}
{center}
<div class="sub">{sub}</div><div class="big">{a}</div><div class="mid">{b}</div><div class="line"></div>{lk}
<div class="foot">星と数のこよみ　よみ</div></body></html>"""


def stars(seed):
    r = random.Random(seed); s = []
    for _ in range(70):
        sz = r.uniform(1.5, 4.5)
        s.append(f'<div class="st" style="left:{r.uniform(0,1080):.0f}px;top:{r.uniform(0,1350):.0f}px;width:{sz:.1f}px;height:{sz:.1f}px;opacity:{r.uniform(.3,.9):.2f}"></div>')
    return "".join(s)


def render(img, d, i):
    if img["kind"] == "tarot":
        src = os.path.join(FORTUNE, "app", "img", "tarot", f"{img['card']:02d}.jpg")
        center = f'<img class="card" src="file://{src}">'
    elif img["kind"] == "star":
        center = f'<div class="mark">{img["mark"]}&#xFE0E;</div>'
    else:
        center = '<img class="icon" src="x-icon.png">'
    lk = ""
    if img.get("lucky"):
        c, it, f = img["lucky"]
        lk = f'<div class="lk"><b>今日のラッキー</b><br>{c} ・ {it} ・ {f}</div>'
    size = 104 if len(img["a"]) <= 8 else 88
    html = os.path.join(HERE, f"{d}.html")
    open(html, "w", encoding="utf-8").write(PAGE.format(center=center, sub=img["sub"], a=img["a"], b=img["b"], lk=lk, size=size, stars=stars(i)))
    png = os.path.join(HERE, f"{d}.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1080,1350",
                    "--allow-file-access-from-files", f"--screenshot={png}", "file://" + html], capture_output=True)
    jpg = os.path.join(REPO, "docs", "images", f"{d}.jpg")  # Instagram は JPEG を使う
    subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "90", png, "--out", jpg], check=True, capture_output=True)
    os.remove(png)


def main():
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date(2026, 12, 1)
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
    shutil.copy(os.path.join(FORTUNE, "sns", "x-icon.png"), os.path.join(HERE, "x-icon.png"))
    names = {"intro": "はじめまして", "tarot": "今日のタロット", "star": "今日のラッキー星座", "num": "数秘のひとこと"}
    review = ["# よみの投稿（確認用・make-images/make.py が作る）", "",
              "日替わり：はじめまして → 今日のタロット → 今日のラッキー星座 → 数秘のひとこと → タロット…のくり返し。",
              "日付は仮です。本番の前に make.py に最初の日を渡して作り直せます。",
              "画像は図形で描いたよみ・1910年のタロット原画（パブリックドメイン）・星座の記号だけで、AI画像はありません。", ""]
    for i, (kind, ig, th, img) in enumerate(build(start, days)):
        d = (start + timedelta(days=i)).isoformat()
        render(img, d, i)
        json.dump({"date": d, "kind": kind, "image": f"{d}.jpg", "ai_generated": False, "instagram": ig, "threads": th},
                  open(os.path.join(REPO, "posts", f"{d}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        review += [f"## {i+1}日目 {d} {names[kind]}（画像 docs/images/{d}.jpg）", "", "### Instagram", "```", ig, "```", "",
                   "### Threads", "```", th, "```", ""]
        print("ok", d, kind, len(ig), len(th))
    open(os.path.join(REPO, "..", "posts-review.md"), "w", encoding="utf-8").write("\n".join(review))


if __name__ == "__main__":
    main()
