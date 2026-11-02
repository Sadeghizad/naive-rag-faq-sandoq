"""Naive RAG over faq_qa_pairs.csv: BM25 retrieval + one LLM call.

    python ask.py "برای دریافت ضمانت‌نامه چه شرایطی لازم است؟"
    python ask.py --retrieve-only "لیزینگ"      # no LLM / no network needed
    python ask.py --selftest                    # offline checks
"""
import argparse
import csv
import math
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "faq_qa_pairs.csv"

SYSTEM = (
    "تو دستیار پرسش‌وپاسخ «صندوق نوآوری و شکوفایی» هستی. فقط بر اساس «منابع» پاسخ بده و "
    "چیزی از خودت اضافه نکن. اگر پاسخ در منابع نبود، صریح بگو در پرسش‌های متداول پیدا نشد. "
    "پاسخ را فارسی، کوتاه و دقیق بده و در پایان شماره منبع را ذکر کن."
)


# ---------------------------------------------------------------- text prep
_CHARMAP = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "أ": "ا", "إ": "ا", "ؤ": "و", "ﻻ": "لا"})
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_PUNCT = re.compile(r"[\W_]+", re.UNICODE)


def normalize(text: str) -> str:
    """Unify Arabic/Persian look-alike letters, digits, diacritics and ZWNJ."""
    text = unicodedata.normalize("NFC", text).translate(_CHARMAP).translate(_DIGITS)
    text = _DIACRITICS.sub("", text).replace("\u200c", " ")
    return _PUNCT.sub(" ", text).lower()


def tokens(text: str) -> list[str]:
    # ponytail: no Persian stemmer (میشود/شود، ها/های). BM25 idf carries FAQ term matching;
    # add a stemmer only if users report misses on inflected forms.
    return normalize(text).split()


# ------------------------------------------------------------------- BM25
class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.tfs = [Counter(tokens(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = (sum(self.lens) / len(docs)) if docs else 1.0
        self.k1, self.b = k1, b
        df = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}

    def search(self, query: str, k: int = 4) -> list[tuple[float, int]]:
        scored = []
        for i, tf in enumerate(self.tfs):
            score = 0.0
            norm = self.k1 * (1 - self.b + self.b * self.lens[i] / self.avgdl)
            for term in tokens(query):
                f = tf.get(term, 0)
                if f:
                    score += self.idf[term] * f * (self.k1 + 1) / (f + norm)
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return scored[:k]


# -------------------------------------------------------------------- data
def load_docs(path: Path = CSV_PATH) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    docs = []
    for r in rows:
        q = (r.get("question") or "").strip()
        a = (r.get("answer") or "").strip()
        c = (r.get("category") or "").strip()
        if q and a:
            # index category + question + answer so category wording is searchable too
            docs.append({"category": c, "question": q, "answer": a, "text": f"{c} {q} {a}"})
    return docs


def load_env(path: Path = ROOT / ".env") -> None:
    """Tiny .env loader — no python-dotenv dependency."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))


# --------------------------------------------------------------------- LLM
def llm_answer(question: str, hits: list[dict]) -> str:
    from openai import OpenAI  # imported here so --selftest works offline

    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.b.ai/v1"),
    )
    context = "\n\n".join(
        f"[منبع {i}] دسته: {d['category']}\nسوال: {d['question']}\nپاسخ: {d['answer']}"
        for i, d in enumerate(hits, 1)
    )
    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "minimax-m3.1-flash"),
        temperature=0.3,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"منابع:\n{context}\n\nسوال کاربر: {question}"},
        ],
    )
    msg = resp.choices[0].message
    return (msg.content or "").strip() or (getattr(msg, "reasoning_content", "") or "").strip()


# ------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Naive RAG over the صندوق نوآوری FAQ")
    p.add_argument("question", nargs="*", help="سوال کاربر")
    p.add_argument("-k", type=int, default=4, help="تعداد منابع بازیابی‌شده (default 4)")
    p.add_argument("--retrieve-only", action="store_true", help="فقط بازیابی، بدون LLM")
    p.add_argument("--selftest", action="store_true", help="اجرای تست‌های آفلاین")
    args = p.parse_args(argv)

    docs = load_docs()
    index = BM25([d["text"] for d in docs])

    if args.selftest:
        return selftest(index, docs)

    question = " ".join(args.question).strip()
    if not question:
        p.error("سوال را وارد کنید، مثال: python ask.py \"شرایط ضمانت‌نامه چیست؟\"")

    hits = [docs[i] for _, i in index.search(question, args.k)]
    if not hits:
        print("هیچ سوال مرتبطی در پرسش‌های متداول پیدا نشد.")
        return 0

    if args.retrieve_only:
        for i, d in enumerate(hits, 1):
            print(f"[{i}] ({d['category']}) {d['question']}\n    {d['answer'][:200]}...\n")
        return 0

    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY تنظیم نشده است. فایل .env را بسازید یا از --retrieve-only استفاده کنید.", file=sys.stderr)
        return 1

    print(llm_answer(question, hits))
    print("\n--- منابع ---")
    for i, d in enumerate(hits, 1):
        print(f"[{i}] ({d['category']}) {d['question']}")
    return 0


def selftest(index: BM25, docs: list[dict]) -> int:
    assert normalize("دانش‌بنیان") == "دانش بنیان"
    assert normalize("شركت ي ك") == "شرکت ی ک"
    assert normalize("۱۲۳") == "123"
    assert tokens("شرکت‌های دانش‌بنیان") == ["شرکت", "های", "دانش", "بنیان"]

    def cats(query: str) -> list[str]:
        return [docs[i]["category"] for _, i in index.search(query, 3)]

    assert "ضمانت‌نامه" in cats("برای دریافت ضمانت نامه چه شرایطی لازم است؟")
    assert "فروش اقساطی (لیزینگ و سفارش ساخت)" in cats("لیزینگ")
    assert "ودیعه رهن" in cats("ودیعه رهن چگونه است؟")
    # nonsense must not match everything
    assert cats("zxqv blorp") == []
    print("selftest OK (%d docs, %d terms)" % (len(docs), len(index.idf)))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Persian text on Windows consoles
    sys.exit(main(sys.argv[1:]))
