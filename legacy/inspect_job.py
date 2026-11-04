import pandas as pd
import html
from bs4 import BeautifulSoup

df = pd.read_csv("jobs.csv")
job = df[df["title"].str.contains("Software Engineer II", case=False, na=False)].iloc[0]

soup = BeautifulSoup(html.unescape(str(job["description"])), "html.parser")

for element in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
    text = element.get_text(" ", strip=True)
    if text:
        print(f"{element.name}: {text}")
