import time
import csv
import os
from datetime import datetime
import re
from collections import Counter

from bs4 import BeautifulSoup as bs
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# For sentiment analysis
try:
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    print("[!] TextBlob not installed. Install with: pip install textblob")
    print("[!] Sentiment analysis will be skipped.")
    SENTIMENT_AVAILABLE = False

# ---------------------------------------------------------------------------------------
# Function to load existing post IDs from CSV file
# ---------------------------------------------------------------------------------------
def load_existing_post_ids(csv_file):
    """Load existing post IDs from CSV file to avoid duplicates"""
    existing_ids = set()
    if os.path.exists(csv_file):
        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    post_id = row.get('Post_ID', '').strip()
                    if post_id:
                        existing_ids.add(post_id)
            print(f"[*] Loaded {len(existing_ids)} existing post IDs from {csv_file}")
        except Exception as e:
            print(f"[!] Error loading existing post IDs: {e}")
    else:
        print(f"[*] CSV file {csv_file} doesn't exist. Will create new file.")
    return existing_ids

# ---------------------------------------------------------------------------------------
# Function to initialize CSV file with headers if it doesn't exist
# ---------------------------------------------------------------------------------------
def initialize_csv_file(csv_file):
    """Initialize CSV file with headers if it doesn't exist"""
    if not os.path.exists(csv_file):
        print(f"[*] Creating new CSV file: {csv_file}")
        with open(csv_file, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file, quoting=csv.QUOTE_ALL)
            writer.writerow([
                "Post_ID",
                "Post_Author_Name",
                "Post_Author_Profile",
                "Post_Author_JobTitle",
                "Post_Content",
                "Post_Reactions",
                "Sentiment",
                "Sentiment_Score",
                "Date_Collected"
            ])
    else:
        print(f"[*] Using existing CSV file: {csv_file}")

# ---------------------------------------------------------------------------------------
# Function to append new post data to CSV file
# ---------------------------------------------------------------------------------------
def append_post_to_csv(csv_file, post_data):
    """Append a single post to the CSV file"""
    with open(csv_file, mode='a', encoding='utf-8', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        writer.writerow(post_data)

# ---------------------------------------------------------------------------------------
# Function to load cookies from a Netscape-format cookies.txt file into Selenium's browser
# ---------------------------------------------------------------------------------------
def load_cookies(browser, file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if not line.startswith('#') and line.strip():
                fields = line.strip().split('\t')
                if len(fields) == 7:
                    cookie = {
                        'domain': fields[0],
                        'flag': fields[1],
                        'path': fields[2],
                        'secure': fields[3],
                        'expiration': fields[4],
                        'name': fields[5],
                        'value': fields[6]
                    }
                    browser.add_cookie({
                        'name': cookie['name'],
                        'value': cookie['value'],
                        'domain': cookie['domain'],
                        'path': cookie['path'],
                        'expiry': int(cookie['expiration']) if cookie['expiration'].isdigit() else None
                    })

# ---------------------------------------------------------------------------------------
# Helper function to convert abbreviated reaction/comment strings (e.g., "1K") to integers
# ---------------------------------------------------------------------------------------
def convert_abbreviated_to_number(s):
    s = s.upper().strip()
    if 'K' in s:
        return int(float(s.replace('K', '')) * 1000)
    elif 'M' in s:
        return int(float(s.replace('M', '')) * 1000000)
    else:
        try:
            return int(s)
        except ValueError:
            return 0

# ---------------------------------------------------------------------------------------
# Helper function to analyze sentiment of text
# ---------------------------------------------------------------------------------------
def analyze_sentiment(text):
    if not SENTIMENT_AVAILABLE or not text:
        return "neutral", 0.0
    
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # Classify sentiment based on polarity
        if polarity > 0.1:
            sentiment = "positive"
        elif polarity < -0.1:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        return sentiment, round(polarity, 3)
    except Exception as e:
        print(f"[!] Error analyzing sentiment: {e}")
        return "neutral", 0.0

def clean_post_content(content):
    if not content:
        return ""
    
    # Replace line breaks with spaces
    content = content.replace('\n', ' ').replace('\r', ' ')
    
    # Replace curly quotes with straight quotes - more comprehensive
    content = content.replace("'", "'").replace("'", "'")
    content = content.replace('"', '"').replace('"', '"')
    content = content.replace('`', "'").replace('´', "'")
    
    # Remove emojis - much more comprehensive approach
    # Main emoji blocks
    content = re.sub(r'[\U0001F600-\U0001F64F]', '', content)  # Emoticons
    content = re.sub(r'[\U0001F300-\U0001F5FF]', '', content)  # Misc symbols
    content = re.sub(r'[\U0001F680-\U0001F6FF]', '', content)  # Transport
    content = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', content)  # Flags
    content = re.sub(r'[\U0001F900-\U0001F9FF]', '', content)  # Supplemental symbols
    content = re.sub(r'[\U0001FA70-\U0001FAFF]', '', content)  # Extended symbols
    
    # Remove additional symbol ranges that include ✅, ❌, ☕, 🟢 etc.
    content = re.sub(r'[\U00002600-\U000026FF]', '', content)  # Miscellaneous symbols (☕, ✅, ❌, etc.)
    content = re.sub(r'[\U00002700-\U000027BF]', '', content)  # Dingbats
    content = re.sub(r'[\U0001F780-\U0001F7FF]', '', content)  # Geometric shapes extended
    content = re.sub(r'[\U0001F800-\U0001F8FF]', '', content)  # Supplemental arrows
    
    # Remove specific problematic emojis that might not be caught
    content = re.sub(r'[❤️💙💚💛💜🖤🤍🤎❣️💕💞💓💗💖💘💝]', '', content)
    content = re.sub(r'[✅❌☕🟢🔴🟡🟠🟣🟤⚫⚪]', '', content)
    content = re.sub(r'[⭐🌟✨💫⚡🔥💯]', '', content)
    content = re.sub(r'[👍👎👏🙌🤝👋]', '', content)
    
    # Remove mathematical and technical symbols that might appear
    content = re.sub(r'[≈≠≤≥±×÷√∞∆∑∏∫]', '', content)
    
    # Remove additional punctuation symbols
    content = re.sub(r'[†‡§¶]', '', content)
    
    # Remove control characters (but keep regular text)
    content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', content)
    
    # Remove markdown-style formatting markers when they're likely formatting
    # Only remove * and _ when they appear to be markdown (paired or multiple)
    content = re.sub(r'\*{1,3}([^*]*)\*{1,3}', r'\1', content)  # *text* or **text** or ***text***
    content = re.sub(r'_{1,3}([^_]*)_{1,3}', r'\1', content)   # _text_ or __text__ or ___text___
    
    # Remove other formatting characters
    content = re.sub(r'[`~]', '', content)  # backticks and tildes
    
    # Remove bullet point characters
    content = re.sub(r'[•◦▪▫‣]', '', content)
    
    # Clean up hashtag formatting
    content = re.sub(r'hashtag\s*#', '#', content, flags=re.IGNORECASE)
    
    # Normalize multiple spaces to single spaces
    content = re.sub(r'\s+', ' ', content)
    
    # Remove leading/trailing whitespace
    content = content.strip()
    
    return content

# ---------------------------------------------------------------------------------------
# Function to generate sentiment analysis report
# ---------------------------------------------------------------------------------------
def generate_sentiment_report(csv_file, report_file):
    print(f"[*] Generating sentiment analysis report from {csv_file}...")
    
    sentiments = []
    sentiment_scores = []
    reactions = []
    authors = []
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sentiment = row.get('Sentiment', 'neutral')
                score = float(row.get('Sentiment_Score', 0.0))
                reaction_count = int(row.get('Post_Reactions', 0))
                author = row.get('Post_Author_Name', 'Unknown')
                
                sentiments.append(sentiment)
                sentiment_scores.append(score)
                reactions.append(reaction_count)
                authors.append(author)
    
    except FileNotFoundError:
        print(f"[!] Error: {csv_file} not found")
        return
    except Exception as e:
        print(f"[!] Error reading {csv_file}: {e}")
        return
    
    if not sentiments:
        print("[!] No data found for sentiment analysis")
        return
    
    # Calculate statistics
    total_posts = len(sentiments)
    sentiment_counts = Counter(sentiments)
    
    # Calculate percentages
    positive_pct = (sentiment_counts['positive'] / total_posts) * 100
    negative_pct = (sentiment_counts['negative'] / total_posts) * 100
    neutral_pct = (sentiment_counts['neutral'] / total_posts) * 100
    
    # Calculate average sentiment score
    avg_sentiment_score = sum(sentiment_scores) / len(sentiment_scores)
    
    # Calculate reactions statistics
    total_reactions = sum(reactions)
    avg_reactions = total_reactions / total_posts if total_posts > 0 else 0
    max_reactions = max(reactions) if reactions else 0
    min_reactions = min(reactions) if reactions else 0
    
    # Author statistics
    author_counts = Counter(authors)
    most_active_author = author_counts.most_common(1)[0] if author_counts else ("Unknown", 0)
    unique_authors = len(set(authors))
    
    # Sentiment by reaction correlation
    positive_reactions = [reactions[i] for i in range(len(sentiments)) if sentiments[i] == 'positive']
    negative_reactions = [reactions[i] for i in range(len(sentiments)) if sentiments[i] == 'negative']
    neutral_reactions = [reactions[i] for i in range(len(sentiments)) if sentiments[i] == 'neutral']
    
    avg_positive_reactions = sum(positive_reactions) / len(positive_reactions) if positive_reactions else 0
    avg_negative_reactions = sum(negative_reactions) / len(negative_reactions) if negative_reactions else 0
    avg_neutral_reactions = sum(neutral_reactions) / len(neutral_reactions) if neutral_reactions else 0
    
    # Generate report timestamp
    report_timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    # Write sentiment analysis report
    with open(report_file, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file, quoting=csv.QUOTE_ALL)
        
        # Write header
        writer.writerow(["Sentiment Analysis Report", ""])
        writer.writerow(["Generated on", report_timestamp])
        writer.writerow(["Source File", csv_file])
        writer.writerow(["", ""])
        
        # Overall statistics
        writer.writerow(["OVERALL STATISTICS", ""])
        writer.writerow(["Total Posts Analyzed", total_posts])
        writer.writerow(["Total Reactions", total_reactions])
        writer.writerow(["Unique Authors", unique_authors])
        writer.writerow(["", ""])
        
        # Sentiment distribution
        writer.writerow(["SENTIMENT DISTRIBUTION", ""])
        writer.writerow(["Positive Posts", f"{sentiment_counts['positive']} ({positive_pct:.1f}%)"])
        writer.writerow(["Negative Posts", f"{sentiment_counts['negative']} ({negative_pct:.1f}%)"])
        writer.writerow(["Neutral Posts", f"{sentiment_counts['neutral']} ({neutral_pct:.1f}%)"])
        writer.writerow(["Average Sentiment Score", f"{avg_sentiment_score:.3f}"])
        writer.writerow(["", ""])
        
        # Reaction statistics
        writer.writerow(["REACTION STATISTICS", ""])
        writer.writerow(["Average Reactions per Post", f"{avg_reactions:.1f}"])
        writer.writerow(["Maximum Reactions", max_reactions])
        writer.writerow(["Minimum Reactions", min_reactions])
        writer.writerow(["", ""])
        
        # Sentiment-Reaction correlation
        writer.writerow(["SENTIMENT-REACTION CORRELATION", ""])
        writer.writerow(["Avg Reactions - Positive Posts", f"{avg_positive_reactions:.1f}"])
        writer.writerow(["Avg Reactions - Negative Posts", f"{avg_negative_reactions:.1f}"])
        writer.writerow(["Avg Reactions - Neutral Posts", f"{avg_neutral_reactions:.1f}"])
        writer.writerow(["", ""])
        
        # Author statistics
        writer.writerow(["AUTHOR STATISTICS", ""])
        writer.writerow(["Most Active Author", f"{most_active_author[0]} ({most_active_author[1]} posts)"])
        writer.writerow(["", ""])
        
        # Top authors by post count
        writer.writerow(["TOP AUTHORS BY POST COUNT", ""])
        writer.writerow(["Author", "Post Count"])
        for author, count in author_counts.most_common(10):  # Top 10 authors
            writer.writerow([author, count])
        
        # Sentiment interpretation
        writer.writerow(["", ""])
        writer.writerow(["SENTIMENT INTERPRETATION", ""])
        if avg_sentiment_score > 0.1:
            overall_sentiment = "Overall Positive"
        elif avg_sentiment_score < -0.1:
            overall_sentiment = "Overall Negative"
        else:
            overall_sentiment = "Overall Neutral"
        
        writer.writerow(["Overall Sentiment", overall_sentiment])
        writer.writerow(["Sentiment Score Range", "-1.0 (very negative) to +1.0 (very positive)"])
        writer.writerow(["", ""])
        
        # Recommendations
        writer.writerow(["INSIGHTS & RECOMMENDATIONS", ""])
        if positive_pct > 60:
            writer.writerow(["Content Performance", "Strong positive sentiment - continue current strategy"])
        elif negative_pct > 40:
            writer.writerow(["Content Performance", "High negative sentiment - review content strategy"])
        else:
            writer.writerow(["Content Performance", "Mixed sentiment - monitor trends"])
        
        if avg_positive_reactions > avg_negative_reactions * 1.5:
            writer.writerow(["Engagement Pattern", "Positive content generates more engagement"])
        elif avg_negative_reactions > avg_positive_reactions * 1.5:
            writer.writerow(["Engagement Pattern", "Negative content generates more engagement"])
        else:
            writer.writerow(["Engagement Pattern", "Similar engagement across sentiment types"])
    
    print(f"[*] Sentiment analysis report generated: {report_file}")
    print(f"[*] Report Summary:")
    print(f"    - Total posts analyzed: {total_posts}")
    print(f"    - Positive: {sentiment_counts['positive']} ({positive_pct:.1f}%)")
    print(f"    - Negative: {sentiment_counts['negative']} ({negative_pct:.1f}%)")
    print(f"    - Neutral: {sentiment_counts['neutral']} ({neutral_pct:.1f}%)")
    print(f"    - Average sentiment score: {avg_sentiment_score:.3f}")
    print(f"    - Overall sentiment: {overall_sentiment}")

# ---------------------------------------------------------------------------------------
# Main script
# ---------------------------------------------------------------------------------------
def main():
    search_url = "https://www.linkedin.com/search/results/content/?keywords=lgindia"
    cookies_file = "www.linkedin.com_cookies.txt" 
    csv_file = "lgindia_posts_final.csv"
    sentiment_report_file = "lgindia_sentiment_report.csv"
    MAX_POSTS = 1000
    MAX_SCROLL_ATTEMPTS = 80
    MAX_NO_NEW_POSTS_IN_A_ROW = 50

    # --------------------------------
    # Initialize CSV file and load existing post IDs
    # --------------------------------
    initialize_csv_file(csv_file)
    existing_post_ids = load_existing_post_ids(csv_file)
    
    # -------------------------------- 
    # Set up undetected Chrome driver
    # --------------------------------
    print("[*] Initializing undetected Chrome driver...") 
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    browser = uc.Chrome(options=chrome_options)
    print("[*] Setting window size...")
    browser.set_window_size(1920, 1080)

    # --------------------------------
    # Log in using cookies
    # --------------------------------
    print(f"[*] Going to LinkedIn home page and loading cookies from {cookies_file} ...")
    browser.get('https://www.linkedin.com/')
    time.sleep(2)
    load_cookies(browser, cookies_file)
    browser.refresh()
    print("[*] Cookies loaded; refreshing page to apply them...")

    try:
        WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#global-nav"))
        )
        print("[*] Successfully logged in (navigation bar found).")
    except TimeoutException:
        print("[!] Navigation bar not found after applying cookies. Exiting.")
        browser.quit()
        return

    print(f"[*] Navigating to {search_url} ...")
    browser.get(search_url)
    time.sleep(5)

    new_posts_added = 0
    total_posts_processed = 0
    skipped_duplicates = 0
    LOAD_PAUSE_TIME = 4
    scroll_attempts = 0
    no_new_posts_count = 0

    print("[*] Starting to scroll and collect post data...")
    print(f"[*] Will skip posts already in database. Currently have {len(existing_post_ids)} existing posts.")
    
    while new_posts_added < MAX_POSTS and scroll_attempts < MAX_SCROLL_ATTEMPTS and no_new_posts_count < MAX_NO_NEW_POSTS_IN_A_ROW:
        soup = bs(browser.page_source, "html.parser")
        post_wrappers = soup.find_all("div", {"class": "feed-shared-update-v2"})
        new_posts_in_this_pass = 0

        for pw in post_wrappers:
            post_id = None
            detail_link_tag = pw.find("a", {"class": "update-components-mini-update-v2__link-to-details-page"})
            if detail_link_tag and detail_link_tag.get("href"):
                post_url = detail_link_tag["href"].strip()
                if "urn:li:activity:" in post_url:
                    post_id = post_url.split("urn:li:activity:")[-1].replace("/", "")
            if not post_id:
                data_urn = pw.get("data-urn", "")
                if "urn:li:activity:" in data_urn:
                    post_id = data_urn.split("urn:li:activity:")[-1]
            if not post_id:
                continue

            total_posts_processed += 1

            # Check if post already exists
            if post_id in existing_post_ids:
                skipped_duplicates += 1
                continue

            # Add to existing_post_ids to avoid processing same post again in this session
            existing_post_ids.add(post_id)
            new_posts_in_this_pass += 1

            author_name = None
            author_profile_link = None
            author_jobtitle = None
            actor_container = pw.find("div", {"class": "update-components-actor__container"})
            if actor_container:
                name_tag = actor_container.find("span", {"class": "update-components-actor__title"})
                if name_tag:
                    inner_span = name_tag.find("span", {"dir": "ltr"})
                    if inner_span:
                        raw_name = inner_span.get_text(strip=True)
                        # Always take first half since it's always duplicated
                        if raw_name:
                            words = raw_name.split()
                            if len(words) >= 2:
                                mid = len(words) // 2
                                author_name = ' '.join(words[:mid])
                            else:
                                author_name = raw_name
                
                actor_link = actor_container.find("a", {"class": "update-components-actor__meta-link"})
                if actor_link and actor_link.get("href"):
                    author_profile_link = actor_link["href"].strip()
                    if author_profile_link.startswith("/in/"):
                        author_profile_link = "https://www.linkedin.com" + author_profile_link
                
                jobtitle_tag = actor_container.find("span", {"class": "update-components-actor__description"})
                if jobtitle_tag:
                    raw_jobtitle = jobtitle_tag.get_text(strip=True)
                    # Always take first half since it's always duplicated
                    if raw_jobtitle:
                        words = raw_jobtitle.split()
                        if len(words) >= 2:
                            mid = len(words) // 2
                            author_jobtitle = ' '.join(words[:mid])
                        else:
                            author_jobtitle = raw_jobtitle
                        # Clean the job title
                        author_jobtitle = clean_post_content(author_jobtitle)

            post_content = None
            content_div = pw.find("div", {"class": "update-components-text"})
            if content_div:
                raw_content = content_div.get_text(separator="\n", strip=True)
                post_content = clean_post_content(raw_content)

            # Analyze sentiment of the post content
            sentiment, sentiment_score = analyze_sentiment(post_content)

            post_reactions = 0
            social_counts_div = pw.find("div", {"class": "social-details-social-counts"})
            if social_counts_div:
                reaction_item = social_counts_div.find("li", {"class": "social-details-social-counts__reactions"})
                if reaction_item:
                    button_tag = reaction_item.find("button")
                    if button_tag and button_tag.has_attr("aria-label"):
                        raw_reactions = button_tag["aria-label"].split(" ")[0]
                        post_reactions = convert_abbreviated_to_number(raw_reactions)

            date_collected = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

            # Prepare post data
            post_data = [
                post_id or "",
                author_name or "",
                author_profile_link or "",
                author_jobtitle or "",
                post_content or "",
                post_reactions,
                sentiment,
                sentiment_score,
                date_collected
            ]

            # Append to CSV file
            append_post_to_csv(csv_file, post_data)

            new_posts_added += 1
            print(f"[+] Added NEW Post ID {post_id}. New posts added: {new_posts_added}")
            print(f"    Author: {author_name} | {author_profile_link}")
            print(f"    Content snippet: {post_content[:70]}{'...' if len(post_content or '')>70 else ''}")
            print(f"    Sentiment: {sentiment} ({sentiment_score})")
            print(f"    Progress: {new_posts_added}/{MAX_POSTS} new posts | {skipped_duplicates} duplicates skipped")

            if new_posts_added >= MAX_POSTS:
                break

        if new_posts_in_this_pass == 0:
            no_new_posts_count += 1
        else:
            no_new_posts_count = 0

        if new_posts_added < MAX_POSTS:
            print(f"[*] Scrolling to load more posts... (Attempt {scroll_attempts + 1}/{MAX_SCROLL_ATTEMPTS})")
            browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(LOAD_PAUSE_TIME)
            scroll_attempts += 1

    print(f"\n[*] Scraping completed!")
    print(f"    - Total posts processed: {total_posts_processed}")
    print(f"    - New posts added: {new_posts_added}")
    print(f"    - Duplicates skipped: {skipped_duplicates}")
    print(f"    - Total posts in database: {len(existing_post_ids)}")
    print("[*] Closing browser.")
    browser.quit()
    print(f"[*] Data appended to {csv_file}")
    
    # Generate sentiment analysis report
    if new_posts_added > 0:
        print("[*] Generating updated sentiment analysis report...")
        generate_sentiment_report(csv_file, sentiment_report_file)
    else:
        print("[*] No new posts added, skipping sentiment report generation.")


if __name__ == "__main__":
    main()