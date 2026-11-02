# naive-rag-faq-sandoq

Retrieval-augmented answers over the FAQ of Iran's National Innovation Fund (صندوق نوآوری و شکوفایی). You ask a question in Persian, the script picks the closest rows from `faq_qa_pairs.csv`, and an OpenAI-compatible model writes the answer from those rows only.

There is no vector store and no embedding model. The retriever is BM25 in roughly forty lines of the Python standard library, and generation is one chat completion. The whole project is one file, `ask.py`.

## Data

`faq_qa_pairs.csv` has 134 rows with three columns: `category`, `question`, `answer`. Answers run from a few words to about 3,300 characters, with a median near 190.

| Rows | Category |
| --- | --- |
| 31 | فروش اقساطی (لیزینگ و سفارش ساخت) |
| 30 | حقوقی(وثایق، تضامین و ...) |
| 24 | سرمایه‌گذاری |
| 18 | میز خدمت و پذیرش |
| 8 | ضمانت‌نامه |
| 6 | صکوک |
| 6 | رشد تولید، تثبیت تولید، تامین مالی قرارداد و ضمانت نامه اعتباری |
| 6 | ودیعه رهن |
| 5 | توانمندسازی (کمک بلاعوض) |

`extract_from_site.py` is the scraper that produced the CSV from the fund's FAQ pages at `inif.ir`. Run it again when the fund updates those pages. It needs `requests` and `beautifulsoup4`, which `ask.py` does not.

## Setup

Python 3.11 or newer, plus the official OpenAI client:

```
pip install openai
```

Copy `.env.example` to `.env` and fill in your credentials:

```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.b.ai/v1
OPENAI_MODEL=minimax-m3.1-flash
```

Any endpoint that speaks the OpenAI chat API works: b.ai, AvalAI, DeepSeek, OpenRouter, or a local llama.cpp or Ollama server on an OpenAI-compatible port. Point `OPENAI_BASE_URL` at it and set `OPENAI_MODEL` to a model it serves. `.env` is listed in `.gitignore`, so keep the only copy of a live key there and not in a tracked file.

## Use

```
python ask.py "برای دریافت ضمانت‌نامه چه شرایطی لازم است؟"
python ask.py -k 6 "شرایط سرمایه‌گذاری چیست؟"
python ask.py --retrieve-only "لیزینگ"
python ask.py --selftest
```

`-k` sets how many rows feed the prompt, 4 by default. `--retrieve-only` prints the matches and skips the model call, which is what you want when testing retrieval or working without a network. `--selftest` runs offline assertions over the normalizer and the index and needs no key.

A normal run prints the answer, then the category and question of each row it used, so you can check the model against the source.

## How it works

Persian text is normalized before anything else: Arabic letter forms become Persian ones (`ي` to `ی`, `ك` to `ک`), Arabic-Indic digits become ASCII, diacritics are stripped, and the zero-width non-joiner becomes a space, so `دانش‌بنیان` and `دانش بنیان` index the same. Punctuation splits words and everything is lowercased.

Each row is indexed as one document of category, question, and answer, scored with BM25 at `k1=1.5`, `b=0.75`. Keeping whole answers as documents suits this data because the rows are already short and a match on any part of an answer usually means the row is relevant.

The top rows go into the prompt as numbered sources. The system prompt restricts the model to those sources, asks for a short Persian answer, and requires it to say `در پرسش‌های متداول پیدا نشد` when the sources do not cover the question. That refusal works in practice: asking about the fund's office hours, which the CSV does not cover, returns the refusal instead of a guess.

## Limits

The retriever is lexical, so a question that shares no word with the relevant answer will not find it. Persian inflection causes most of the misses: `وام` and `تسهیلات` are different tokens, and the tokenizer does no stemming, so `می‌شود` does not match `شود`. Add a stemmer or swap in embeddings if users report misses on paraphrased questions.

Answers stop at the CSV. The model knows nothing about the fund beyond those rows, and the rows are a snapshot of pages that change with the fund's regulations. Treat the output as a pointer to the right document and keep the source list for verification.

One question per run. There is no conversation state and no re-ranking of the retrieved rows.
