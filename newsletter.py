import feedparser
import requests
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime
import concurrent.futures
import hashlib
import os
import smtplib
from email.mime.text import MIMEText

# -----------------------------
# CONFIG
# -----------------------------

GROQ_API_KEY=os.getenv("GROQ_API_KEY")

EMAIL_USER=os.getenv("EMAIL_USER")
EMAIL_PASS=os.getenv("EMAIL_PASS")
EMAIL_TO=os.getenv("EMAIL_TO")

MODEL="llama-3.1-8b-instant"

client=Groq(api_key=GROQ_API_KEY)

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
Classify this cybersecurity news into ONE of these categories:

Ransomware
Zero-Day
Data Breach
Malware
Vulnerability
Nation State

Return ONLY the category name.

News:
{title}
"""

    completion=client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}]
    )

    category=completion.choices[0].message.content.strip()

    allowed=[
        "Ransomware",
        "Zero-Day",
        "Data Breach",
        "Malware",
        "Vulnerability",
        "Nation State"
    ]

    if category not in allowed:
        category="Vulnerability"

    return category


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
# AGENT 5 — SCRAPER
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
Summarize this cybersecurity news in about 60 words:

{text}

return only the summary
"""

    completion=client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}]
    )

    return completion.choices[0].message.content


# -----------------------------
# AGENT 7 — REPORT BUILDER
# -----------------------------

def build_html(news):

    today=datetime.now().strftime("%d %B %Y")

    html=f"""
<html>
<head>
<title>Cybersecurity Intelligence Brief</title>
</head>

<body style="font-family:Arial">

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

<a href="{n['link']}">Read Full Article</a>

"""

    html+="</body></html>"

    return html


# -----------------------------
# LINKEDIN POST GENERATOR
# -----------------------------

def linkedin_post(news):

    post="Cybersecurity Intelligence Brief\n\n"

    for i,n in enumerate(news[:5]):

        post+=f"{i+1}. {n['title']}\n"
        post+=f"Threat: {n['category']} | Severity: {n['score']}/10\n"
        post+=f"{n['summary']}\n\n"

    post+="\n#cybersecurity #infosec #threatintel"

    return post


# -----------------------------
# EMAIL SENDER
# -----------------------------

def send_email(html):

    if EMAIL_USER is None:
        return

    msg=MIMEText(html,"html")

    msg["Subject"]="Cybersecurity Intelligence Brief"
    msg["From"]=EMAIL_USER
    msg["To"]=EMAIL_TO

    server=smtplib.SMTP_SSL("smtp.gmail.com",465)

    server.login(EMAIL_USER,EMAIL_PASS)

    server.sendmail(EMAIL_USER,EMAIL_TO,msg.as_string())

    server.quit()

#------------------------------
# Generate Daily Homepage
#------------------------------
def build_homepage(news):

    today=datetime.now().strftime("%d %B %Y")

    html=f"""
<html>
<head>
<title>Cyber Threat Intelligence Portal</title>
</head>

<body style="font-family:Arial">

<h1>Global Cyber Threat Intelligence</h1>
<h3>{today}</h3>

<h2>Top 10 Global Cyber Threats</h2>

"""

    for i,n in enumerate(news[:10]):

        html+=f"""
<h3>{i+1}. {n['title']}</h3>
<b>Category:</b> {n['category']} |
<b>Severity:</b> {n['score']}/10

<p>{n['summary']}</p>
<a href="{n['link']}">Read more</a>
<hr>
"""

    html+="</body></html>"

    return html

#------------------------------
# CATEGORY PAGES
#------------------------------

from collections import defaultdict

def build_category_pages(news):

    categories=defaultdict(list)

    for n in news:
        categories[n["category"]].append(n)

    os.makedirs("docs/categories",exist_ok=True)

    for cat,items in categories.items():

        html=f"<h1>{cat} Threat Intelligence</h1>"

        for n in items:

            html+=f"""
<h3>{n['title']}</h3>
Severity: {n['score']}/10
<p>{n['summary']}</p>
<a href="{n['link']}">Source</a>
<hr>
"""

    safe_cat = cat.lower().replace(" ", "_")[:40]

    with open(f"docs/categories/{safe_cat}.html","w",encoding="utf8") as f:
        f.write(html)


#------------------------------
# Report Archive
#------------------------------

def save_archive(html):

    os.makedirs("docs/archive",exist_ok=True)

    date=str(datetime.now().date())

    with open(f"docs/archive/{date}.html","w",encoding="utf8") as f:
        f.write(html)


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

    for a in articles[:45]:

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

    # Save archive report
    save_archive(html)

    # Generate category pages
    build_category_pages(results)

    # Generate homepage
    homepage=build_homepage(results)
    
    os.makedirs("docs",exist_ok=True)

    with open("docs/index.html","w",encoding="utf8") as f:
        f.write(homepage)

    # LinkedIn post
    os.makedirs("linkedin_posts",exist_ok=True)
    
    post=linkedin_post(results)

    with open(f"linkedin_posts/linkedin_post_{datetime.now().date()}.txt","w") as f:
        f.write(post)

    send_email(html)

    with open("docs/index.html","w",encoding="utf8") as f:
        f.write(html)

    print("Report generated:",file)

  


run()
