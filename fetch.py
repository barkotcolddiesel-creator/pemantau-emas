import datetime
import json
import os
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; harga-emas-pribadi/1.0)"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def world():
    j = json.loads(get("https://api.gold-api.com/price/XAU"))
    return round(float(j["price"]), 2)


def antam():
    html = get("https://www.logammulia.com/id/harga-emas-hari-ini")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    m = re.search(r"\b1\s*gr(?:am)?\b\s*(?:Rp\.?)?\s*([\d.,]{7,12})", text, re.I)
    if not m:
        raise ValueError("baris 1 gram tidak ditemukan")
    v = int(re.sub(r"\D", "", m.group(1)))
    if not 100_000 <= v <= 100_000_000:
        raise ValueError(f"angka tidak masuk akal: {v}")
    return v


def rp(v):
    return "Rp " + f"{v:,.0f}".replace(",", ".")


def usd(v):
    return f"${v:,.2f}"


def line(label, key, fmt, data, today):
    cur = next((r[key] for r in data if r["d"] == today), None)
    if cur is None:
        return f"{label}: gagal diambil"
    prev = next((r[key] for r in reversed(data) if r["d"] < today and r[key] is not None), None)
    if prev is None:
        return f"{label}: {fmt(cur)}"
    d = cur - prev
    arah = "naik" if d > 0 else "turun" if d < 0 else "tetap"
    pct = abs(d) / prev * 100
    return f"{label}: {fmt(cur)} ({arah} {fmt(abs(d))}, {pct:.2f}%)"


def notify(msg):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC kosong, notif dilewati")
        return
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=msg.encode("utf-8"),
        headers={"Title": "Harga emas hari ini", "Tags": "coin"},
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    wib = datetime.timezone(datetime.timedelta(hours=7))
    today = datetime.datetime.now(wib).strftime("%Y-%m-%d")
    try:
        data = json.load(open("data.json"))
    except Exception:
        data = []
    row = next((r for r in data if r["d"] == today), None)
    if row is None:
        row = {"d": today, "a": None, "w": None}
        data.append(row)
    errs = []
    for key, fn in (("a", antam), ("w", world)):
        try:
            row[key] = fn()
        except Exception as e:
            errs.append(f"{key}: {e}")
    data.sort(key=lambda r: r["d"])
    json.dump(data, open("data.json", "w"), indent=1)
    msg = "\n".join(
        [
            line("Antam/gram", "a", rp, data, today),
            line("Emas dunia/ons", "w", usd, data, today),
        ]
    )
    print(msg)
    for e in errs:
        print("ERROR", e)
    notify(msg)


main()
