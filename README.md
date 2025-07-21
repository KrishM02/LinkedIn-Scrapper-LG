# LinkedIn Scraper & Sentiment Analyzer

This project uses Selenium (via `undetected_chromedriver`) to scrape LinkedIn posts based on a keyword, and performs **sentiment analysis** on the scraped content using **TextBlob**. Results are saved to a CSV file, and a detailed **sentiment report** is generated automatically.

> ✅ Designed for **Python 3.11.7**

---

## 📦 Features

- Scrapes posts from LinkedIn’s content search
- Captures:
  - Author name & profile link
  - Job title
  - Post content
  - Reaction count
- Filters out duplicates using Post IDs
- Cleans and sanitizes post content
- Performs **sentiment analysis** (positive/negative/neutral)
- Saves data to a CSV file
- Generates an automated sentiment analysis report

---

## 🧰 Requirements

Install all dependencies using:

```bash
pip install -r requirements.txt
