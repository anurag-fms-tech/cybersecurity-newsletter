import feedparser
import requests
from bs4 import BeautifulSoup
from groq import Groq
from datetime import datetime

GROQ_API_KEY="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"

client = Groq(api_key=GROQ_API_KEY)

RSS_FEEDS = [
"https://thehackernews.com/feeds/posts/default",
"https://krebsonsecurity.com/feed/",
"https://www.darkreading.com/rss.xml",
"https://www.bleepingcomputer.com/feed/"
]

def collect_articles():

    articles=[]

    for feed in RSS_FEEDS:

        parsed=feedparser.parse(feed)

        for entry in parsed.entries[:5]:

            articles.append({
                "title":entry.title,
                "link":entry.link
            })

    return articles


def scrape_article(url):

    html=requests.get(url).text

    soup=BeautifulSoup(html,"html.parser")

    paragraphs=[p.text for p in soup.find_all("p")]

    return " ".join(paragraphs[:10])


def summarize(text):

    prompt=f"Summarize this news in 50 words:\n{text}"

    completion=client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"user","content":prompt}]
    )

    return completion.choices[0].message.content


def generate_newsletter():

    articles=collect_articles()

    newsletter=[]

    for a in articles[:6]:

        text=scrape_article(a["link"])

        summary=summarize(text)

        newsletter.append({
            "title":a["title"],
            "summary":summary,
            "link":a["link"]
        })

    today=datetime.now().strftime("%d %B %Y")

    print("\nCybersecurity Morning Brief",today)

    for i,n in enumerate(newsletter):

        print("\n",i+1,n["title"])
        print(n["summary"])
        print(n["link"])


generate_newsletter()