import csv
import re
import sys
from typing import List, Tuple

import requests
import os
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
WEBSITES = [
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D9%85%DB%8C%D8%B2+%D8%AE%D8%AF%D9%85%D8%AA+%D9%88+%D9%BE%D8%B0%DB%8C%D8%B1%D8%B4&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=505",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D8%AA%D9%88%D8%A7%D9%86%D9%85%D9%86%D8%AF%D8%B3%D8%A7%D8%B2%DB%8C+%28%DA%A9%D9%85%DA%A9+%D8%A8%D9%84%D8%A7%D8%B9%D9%88%D8%B6%29&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=503",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D8%B6%D9%85%D8%A7%D9%86%D8%AA%E2%80%8C%D9%86%D8%A7%D9%85%D9%87&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=502",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D8%B3%D8%B1%D9%85%D8%A7%DB%8C%D9%87%E2%80%8C%DA%AF%D8%B0%D8%A7%D8%B1%DB%8C&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=801",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D8%AD%D9%82%D9%88%D9%82%DB%8C%28%D9%88%D8%AB%D8%A7%DB%8C%D9%82%D8%8C+%D8%AA%D8%B6%D8%A7%D9%85%DB%8C%D9%86+%D9%88+...%29&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=506",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D9%88%D8%AF%DB%8C%D8%B9%D9%87+%D8%B1%D9%87%D9%86&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=1001",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D9%81%D8%B1%D9%88%D8%B4+%D8%A7%D9%82%D8%B3%D8%A7%D8%B7%DB%8C+%28%D9%84%DB%8C%D8%B2%DB%8C%D9%86%DA%AF+%D9%88+%D8%B3%D9%81%D8%A7%D8%B1%D8%B4+%D8%B3%D8%A7%D8%AE%D8%AA%29&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=1002",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D8%B5%DA%A9%D9%88%DA%A9&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=1003",
    "https://www.inif.ir/web/guest/faq?p_p_id=faqdisplay_INSTANCE_AnDgfdjODWCm&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_faqdisplay_INSTANCE_AnDgfdjODWCm_sectionName=%D8%B1%D8%B4%D8%AF+%D8%AA%D9%88%D9%84%DB%8C%D8%AF%D8%8C+%D8%AA%D8%AB%D8%A8%DB%8C%D8%AA+%D8%AA%D9%88%D9%84%DB%8C%D8%AF%D8%8C+%D8%AA%D8%A7%D9%85%DB%8C%D9%86+%D9%85%D8%A7%D9%84%DB%8C+%D9%82%D8%B1%D8%A7%D8%B1%D8%AF%D8%A7%D8%AF+%D9%88+%D8%B6%D9%85%D8%A7%D9%86%D8%AA+%D9%86%D8%A7%D9%85%D9%87+%D8%A7%D8%B9%D8%AA%D8%A8%D8%A7%D8%B1%DB%8C&_faqdisplay_INSTANCE_AnDgfdjODWCm_code=1004",
]

OUTPUT_FILE = "qa_pairs.csv"
TIMEOUT = 15000  # seconds


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def normalize(text: str) -> str:
    """Collapse runs of whitespace/newlines into a single space."""
    return re.sub(r"\s+", " ", text).strip()


def extract_page_qa(html: str) -> Tuple[str, List[Tuple[str, str]]]:
    soup = BeautifulSoup(html, "html.parser")

    # Category: <h1> inside <header class="faq-question-header clearfix">
    cat_hdr = soup.find("header", class_="faq-question-header clearfix")
    if cat_hdr:
        h1 = cat_hdr.find("h1")
        category = normalize(h1.get_text()) if h1 else ""
    else:
        category = ""

    qa_list = []
    for header in soup.find_all("header", class_="question-item-header"):
        question = normalize(header.get_text())

        # find the next div with both classes question-item and clearfix
        answer_div = header.find_next(
            "div",
            class_=["question-item", "clearfix"]
        )
        answer = normalize(answer_div.get_text(separator=" ")) if answer_div else ""

        if question and answer:
            qa_list.append((question, answer))

    return category, qa_list

def scrape_site(url: str) -> Tuple[str, List[Tuple[str, str]]]:
    try:
        resp = requests.get(
            url, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"}
        )
        resp.raise_for_status()
        return extract_page_qa(resp.text)
    except Exception as exc:
        print(f"[WARN] Failed to process {url}: {exc}", file=sys.stderr)
        return "", []


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main(urls: List[str], out_file: str):
    # ------------------------------------------------------------------
    # 1. Load categories that are already in the CSV
    # ------------------------------------------------------------------
    seen_categories = set()
    try:
        with open(out_file, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)               # skip header
            for row in reader:
                if row:                      # ignore blank lines
                    seen_categories.add(row[0])
    except FileNotFoundError:
        # File does not exist yet – nothing to skip
        pass

    # ------------------------------------------------------------------
    # 2. Scrape only the URLs whose category is *not* already stored
    # ------------------------------------------------------------------
    rows = []
    for url in urls:
        print(f"[INFO] Checking {url}")
        # we need the category to decide whether to skip
        category, qa_list = scrape_site(url)
        if not category:
            continue                       # nothing useful came back

        if category in seen_categories:
            print(f"[SKIP] Category '{category}' already present – skipping.")
            continue

        for q, a in qa_list:
            rows.append((category, q, a))

    # ------------------------------------------------------------------
    # 3. Append the new rows to the CSV (header is written only once)
    # ------------------------------------------------------------------
    file_exists = os.path.isfile(out_file)
    with open(out_file, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["category", "question", "answer"])
        writer.writerows(rows)

    print(f"[DONE] Appended {len(rows)} new QA rows to {out_file}")


if __name__ == "__main__":
    main(WEBSITES, OUTPUT_FILE)