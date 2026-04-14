import feedparser
import requests
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime
import concurrent.futures
import hashlib
import os

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

MODEL="llama-3.1-8b-instant"

with open("rss.txt","r") as f:
    RSS_FEEDS=f.read().splitlines()


# -----------------------------
# AGENT 1 — FEED HARVESTER
# -----------------------------

def fetch_feed(url):

    articles=[]

    try:

        feed=feedparser.parse(url)

        for e in feed.entries[:5]:

            articles.append({
                "title":e.title,
                "link":e.link
            })

    except:
        pass

    return articles


def collect_articles():

    all_articles=[]

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:

        results=list(executor.map(fetch_feed,RSS_FEEDS))

    for r in results:
        all_articles.extend(r)

    return all_articles


# -----------------------------
# AGENT 2 — DEDUPLICATION
# -----------------------------

def deduplicate(articles):

    seen=set()

    unique=[]

    for a in articles:

        h=hashlib.md5(a["title"].encode()).hexdigest()

        if h not in seen:

            seen.add(h)

            unique.append(a)

    return unique


# -----------------------------
# AGENT 3 — CLASSIFIER
# -----------------------------

def classify(title):

    prompt=f"""
Classify this cybersecurity news:

Categories:
Ransomware
Zero-Day
Data Breach
Malware
Vulnerability
Nation State

News:
{title}

Return only the category.
"""

    completion=client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}]
    )

    return completion.choices[0].message.content.strip()


# -----------------------------
# AGENT 4 — SEVERITY SCORER
# -----------------------------

def score(title):

    prompt=f"""
Rate the cybersecurity severity of this news from 1 to 10.

News:
{title}

Return only a number.
"""

    completion=client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}]
    )

    return completion.choices[0].message.content.strip()


# -----------------------------
# AGENT 5 — ARTICLE SCRAPER
# -----------------------------

def scrape(url):

    try:

        html=requests.get(url,timeout=10).text

        soup=BeautifulSoup(html,"html.parser")

        p=[x.text for x in soup.find_all("p")]

        return " ".join(p[:10])

    except:

        return ""


# -----------------------------
# AGENT 6 — AI ANALYST
# -----------------------------

def summarize(text):

    if text=="":

        return "Summary unavailable"

    prompt=f"""
Summarize the cybersecurity news<<<

{text}>>>

return only the summary
"""

    completion=client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}]
    )

    return completion.choices[0].message.content


# -----------------------------
# AGENT 7 — NEWSLETTER BUILDER
# -----------------------------

def build_html(news):

    today=datetime.now().strftime("%d %B %Y")

    html=f"""
    <html>
    <head>
    <title>Cybersecurity Intelligence Brief</title>
    </head>
    <body>
    <h1>Cybersecurity Intelligence Brief</h1>
    <h3>{today}</h3>
    """

    for n in news:

        html+=f"""
        <hr>
        <h2>{n['title']}</h2>
        <b>Threat:</b> {n['category']}<br>
        <b>Severity:</b> {n['score']}/10<br>
        <p>{n['summary']}</p>
        <a href="{n['link']}">Read more</a>
        """

    html+="</body></html>"

    return html


# -----------------------------
# MAIN PIPELINE
# -----------------------------

def run():

    print("Collecting feeds...")

    articles=collect_articles()

    print("Total:",len(articles))

    articles=deduplicate(articles)

    print("After dedup:",len(articles))

    results=[]

    for a in articles[:15]:

        text=scrape(a["link"])

        summary=summarize(text)

        category=classify(a["title"])

        severity=score(a["title"])

        results.append({
            "title":a["title"],
            "summary":summary,
            "link":a["link"],
            "category":category,
            "score":severity
        })

    html=build_html(results)

    os.makedirs("reports",exist_ok=True)

    file=f"reports/report_{datetime.now().date()}.html"

    with open(file,"w",encoding="utf8") as f:

        f.write(html)

    print("Report generated:",file)


run()
