import csv
import os
import sys
from datetime import datetime
from collections import Counter
import argparse

# For sentiment analysis
try:
    from textblob import TextBlob
    SENTIMENT_AVAILABLE = True
except ImportError:
    print("[!] TextBlob not installed. Install with: pip install textblob")
    print("[!] Run: pip install textblob")
    print("[!] Then run: python -m textblob.download_corpora")
    SENTIMENT_AVAILABLE = False

# ---------------------------------------------------------------------------------------
# Helper function to analyze sentiment of text
# ---------------------------------------------------------------------------------------
def analyze_sentiment(text):
    """Analyze sentiment of given text using TextBlob"""
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

# ---------------------------------------------------------------------------------------
# Function to update CSV file with sentiment analysis
# ---------------------------------------------------------------------------------------
def update_csv_with_sentiment(csv_file, backup=True):
    """Update the CSV file with sentiment analysis for posts that don't have it"""
    if not os.path.exists(csv_file):
        print(f"[!] Error: CSV file '{csv_file}' not found!")
        return False
    
    # Create backup if requested
    if backup:
        backup_file = f"{csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"[*] Creating backup: {backup_file}")
        import shutil
        shutil.copy2(csv_file, backup_file)
    
    # Read existing data
    rows = []
    updated_count = 0
    
    print(f"[*] Reading data from {csv_file}...")
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames
            
            # Check if sentiment columns exist
            if 'Sentiment' not in fieldnames:
                fieldnames.append('Sentiment')
            if 'Sentiment_Score' not in fieldnames:
                fieldnames.append('Sentiment_Score')
            
            for row in reader:
                # Check if sentiment analysis is missing or empty
                if not row.get('Sentiment') or not row.get('Sentiment_Score'):
                    content = row.get('Post_Content', '')
                    sentiment, score = analyze_sentiment(content)
                    row['Sentiment'] = sentiment
                    row['Sentiment_Score'] = score
                    updated_count += 1
                    
                    if updated_count % 100 == 0:
                        print(f"[*] Processed {updated_count} posts for sentiment analysis...")
                
                rows.append(row)
    
    except Exception as e:
        print(f"[!] Error reading CSV file: {e}")
        return False
    
    # Write updated data back
    print(f"[*] Writing updated data back to {csv_file}...")
    try:
        with open(csv_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"[*] Updated {updated_count} posts with sentiment analysis")
        return True
    
    except Exception as e:
        print(f"[!] Error writing CSV file: {e}")
        return False

# ---------------------------------------------------------------------------------------
# Function to validate CSV file structure
# ---------------------------------------------------------------------------------------
def validate_csv_structure(csv_file):
    """Validate that the CSV file has the required columns"""
    required_columns = ['Post_ID', 'Post_Author_Name', 'Post_Content', 'Post_Reactions']
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or []
            
            missing_columns = [col for col in required_columns if col not in fieldnames]
            
            if missing_columns:
                print(f"[!] Missing required columns: {missing_columns}")
                print(f"[!] Available columns: {fieldnames}")
                return False
            
            return True
    
    except Exception as e:
        print(f"[!] Error validating CSV structure: {e}")
        return False

# ---------------------------------------------------------------------------------------
# Function to generate comprehensive sentiment analysis report
# ---------------------------------------------------------------------------------------
def generate_sentiment_report(csv_file, report_file=None, detailed=False):
    """Generate a comprehensive sentiment analysis report from CSV data"""
    
    if not os.path.exists(csv_file):
        print(f"[!] Error: CSV file '{csv_file}' not found!")
        return False
    
    if not validate_csv_structure(csv_file):
        print("[!] CSV file structure validation failed!")
        return False
    
    # Set default report filename if not provided
    if not report_file:
        base_name = os.path.splitext(csv_file)[0]
        report_file = f"{base_name}_sentiment_report.csv"
    
    print(f"[*] Generating sentiment analysis report from {csv_file}...")
    
    # Data containers
    sentiments = []
    sentiment_scores = []
    reactions = []
    authors = []
    contents = []
    dates = []
    post_ids = []
    
    # Read and process data
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                sentiment = row.get('Sentiment', 'neutral')
                try:
                    score = float(row.get('Sentiment_Score', 0.0))
                except (ValueError, TypeError):
                    score = 0.0
                
                try:
                    reaction_count = int(row.get('Post_Reactions', 0))
                except (ValueError, TypeError):
                    reaction_count = 0
                
                author = row.get('Post_Author_Name', 'Unknown')
                content = row.get('Post_Content', '')
                date = row.get('Date_Collected', '')
                post_id = row.get('Post_ID', '')
                
                sentiments.append(sentiment)
                sentiment_scores.append(score)
                reactions.append(reaction_count)
                authors.append(author)
                contents.append(content)
                dates.append(date)
                post_ids.append(post_id)
    
    except Exception as e:
        print(f"[!] Error reading {csv_file}: {e}")
        return False
    
    if not sentiments:
        print("[!] No data found for sentiment analysis")
        return False
    
    # Calculate statistics
    total_posts = len(sentiments)
    sentiment_counts = Counter(sentiments)
    
    # Calculate percentages
    positive_pct = (sentiment_counts.get('positive', 0) / total_posts) * 100
    negative_pct = (sentiment_counts.get('negative', 0) / total_posts) * 100
    neutral_pct = (sentiment_counts.get('neutral', 0) / total_posts) * 100
    
    # Calculate average sentiment score
    avg_sentiment_score = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
    
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
    
    # Time-based analysis (if dates available)
    date_analysis = {}
    if dates and any(dates):
        for i, date in enumerate(dates):
            if date:
                date_key = date.split(' ')[0]  # Extract date part
                if date_key not in date_analysis:
                    date_analysis[date_key] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
                date_analysis[date_key][sentiments[i]] += 1
                date_analysis[date_key]['total'] += 1
    
    # Generate report timestamp
    report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Determine overall sentiment
    if avg_sentiment_score > 0.1:
        overall_sentiment = "Overall Positive"
    elif avg_sentiment_score < -0.1:
        overall_sentiment = "Overall Negative"
    else:
        overall_sentiment = "Overall Neutral"
    
    # Write sentiment analysis report
    try:
        with open(report_file, 'w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file, quoting=csv.QUOTE_ALL)
            
            # Write header
            writer.writerow(["LinkedIn Posts Sentiment Analysis Report", ""])
            writer.writerow(["Generated on", report_timestamp])
            writer.writerow(["Source File", csv_file])
            writer.writerow(["Total Posts Analyzed", total_posts])
            writer.writerow(["", ""])
            
            # Overall statistics
            writer.writerow(["=== OVERALL STATISTICS ===", ""])
            writer.writerow(["Total Posts", total_posts])
            writer.writerow(["Total Reactions", f"{total_reactions:,}"])
            writer.writerow(["Unique Authors", unique_authors])
            writer.writerow(["Average Reactions per Post", f"{avg_reactions:.1f}"])
            writer.writerow(["", ""])
            
            # Sentiment distribution
            writer.writerow(["=== SENTIMENT DISTRIBUTION ===", ""])
            writer.writerow(["Positive Posts", f"{sentiment_counts.get('positive', 0):,} ({positive_pct:.1f}%)"])
            writer.writerow(["Negative Posts", f"{sentiment_counts.get('negative', 0):,} ({negative_pct:.1f}%)"])
            writer.writerow(["Neutral Posts", f"{sentiment_counts.get('neutral', 0):,} ({neutral_pct:.1f}%)"])
            writer.writerow(["Average Sentiment Score", f"{avg_sentiment_score:.3f}"])
            writer.writerow(["Overall Sentiment", overall_sentiment])
            writer.writerow(["", ""])
            
            # Reaction statistics
            writer.writerow(["=== REACTION STATISTICS ===", ""])
            writer.writerow(["Maximum Reactions", f"{max_reactions:,}"])
            writer.writerow(["Minimum Reactions", f"{min_reactions:,}"])
            writer.writerow(["Average Reactions", f"{avg_reactions:.1f}"])
            writer.writerow(["", ""])
            
            # Sentiment-Reaction correlation
            writer.writerow(["=== SENTIMENT-REACTION CORRELATION ===", ""])
            writer.writerow(["Avg Reactions - Positive Posts", f"{avg_positive_reactions:.1f}"])
            writer.writerow(["Avg Reactions - Negative Posts", f"{avg_negative_reactions:.1f}"])
            writer.writerow(["Avg Reactions - Neutral Posts", f"{avg_neutral_reactions:.1f}"])
            writer.writerow(["", ""])
            
            # Author statistics
            writer.writerow(["=== AUTHOR STATISTICS ===", ""])
            writer.writerow(["Most Active Author", f"{most_active_author[0]} ({most_active_author[1]} posts)"])
            writer.writerow(["", ""])
            
            # Top authors by post count
            writer.writerow(["=== TOP AUTHORS BY POST COUNT ===", ""])
            writer.writerow(["Author", "Post Count", "Percentage"])
            for author, count in author_counts.most_common(15):  # Top 15 authors
                percentage = (count / total_posts) * 100
                writer.writerow([author, count, f"{percentage:.1f}%"])
            writer.writerow(["", ""])
            
            # Time-based analysis
            if date_analysis:
                writer.writerow(["=== DAILY SENTIMENT TRENDS ===", ""])
                writer.writerow(["Date", "Positive", "Negative", "Neutral", "Total", "Sentiment Ratio"])
                for date, stats in sorted(date_analysis.items()):
                    sentiment_ratio = (stats['positive'] - stats['negative']) / stats['total'] if stats['total'] > 0 else 0
                    writer.writerow([
                        date,
                        stats['positive'],
                        stats['negative'],
                        stats['neutral'],
                        stats['total'],
                        f"{sentiment_ratio:.3f}"
                    ])
                writer.writerow(["", ""])
            
            # Insights and recommendations
            writer.writerow(["=== INSIGHTS & RECOMMENDATIONS ===", ""])
            
            # Content performance insights
            if positive_pct > 60:
                writer.writerow(["Content Performance", "Strong positive sentiment - continue current strategy"])
            elif negative_pct > 40:
                writer.writerow(["Content Performance", "High negative sentiment - review content strategy"])
            else:
                writer.writerow(["Content Performance", "Mixed sentiment - monitor trends and optimize"])
            
            # Engagement insights
            if avg_positive_reactions > avg_negative_reactions * 1.5:
                writer.writerow(["Engagement Pattern", "Positive content generates significantly more engagement"])
            elif avg_negative_reactions > avg_positive_reactions * 1.5:
                writer.writerow(["Engagement Pattern", "Negative content generates more engagement - consider balanced approach"])
            else:
                writer.writerow(["Engagement Pattern", "Similar engagement across sentiment types"])
            
            # Author diversity insights
            if unique_authors < total_posts * 0.1:
                writer.writerow(["Author Diversity", "Low author diversity - consider broadening content sources"])
            else:
                writer.writerow(["Author Diversity", "Good author diversity in content"])
            
            writer.writerow(["", ""])
            
            # Detailed post analysis (if requested)
            if detailed:
                writer.writerow(["=== DETAILED POST ANALYSIS ===", ""])
                writer.writerow(["Post_ID", "Author", "Sentiment", "Score", "Reactions", "Content_Preview"])
                
                # Sort by sentiment score for detailed analysis
                detailed_data = list(zip(post_ids, authors, sentiments, sentiment_scores, reactions, contents))
                detailed_data.sort(key=lambda x: x[3], reverse=True)  # Sort by sentiment score
                
                for post_id, author, sentiment, score, reaction, content in detailed_data:
                    content_preview = content[:100] + "..." if len(content) > 100 else content
                    content_preview = content_preview.replace('\n', ' ').replace('\r', ' ')
                    writer.writerow([post_id, author, sentiment, score, reaction, content_preview])
        
        print(f"[*] Sentiment analysis report generated successfully: {report_file}")
        return True
    
    except Exception as e:
        print(f"[!] Error generating report: {e}")
        return False

# ---------------------------------------------------------------------------------------
# Main function with command line interface
# ---------------------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description='Generate sentiment analysis report from LinkedIn posts CSV')
    parser.add_argument('csv_file', help='Path to the CSV file containing LinkedIn posts data')
    parser.add_argument('-o', '--output', help='Output report file path (default: auto-generated)')
    parser.add_argument('-d', '--detailed', action='store_true', help='Include detailed post analysis in report')
    parser.add_argument('-u', '--update', action='store_true', help='Update CSV file with sentiment analysis for missing entries')
    parser.add_argument('--no-backup', action='store_true', help='Skip creating backup when updating CSV')
    
    args = parser.parse_args()
    
    # Check if file exists
    if not os.path.exists(args.csv_file):
        print(f"[!] Error: CSV file '{args.csv_file}' not found!")
        sys.exit(1)
    
    # Check if TextBlob is available
    if not SENTIMENT_AVAILABLE:
        print("[!] TextBlob is required for sentiment analysis. Please install it first.")
        sys.exit(1)
    
    print(f"[*] Processing CSV file: {args.csv_file}")
    
    # Update CSV with sentiment analysis if requested
    if args.update:
        print("[*] Updating CSV file with sentiment analysis...")
        if not update_csv_with_sentiment(args.csv_file, backup=not args.no_backup):
            print("[!] Failed to update CSV file with sentiment analysis")
            sys.exit(1)
    
    # Generate sentiment analysis report
    print("[*] Generating sentiment analysis report...")
    success = generate_sentiment_report(args.csv_file, args.output, args.detailed)
    
    if success:
        print("[*] Sentiment analysis completed successfully!")
        
        # Print summary
        try:
            with open(args.csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                total_posts = sum(1 for row in reader)
                print(f"[*] Summary: Analyzed {total_posts} posts from {args.csv_file}")
        except:
            pass
    else:
        print("[!] Failed to generate sentiment analysis report")
        sys.exit(1)

# ---------------------------------------------------------------------------------------
# Standalone execution
# ---------------------------------------------------------------------------------------
if __name__ == "__main__":
    # If no command line arguments, run in interactive mode
    if len(sys.argv) == 1:
        print("=== LinkedIn Posts Sentiment Analysis Tool ===")
        print()
        
        # Get CSV file path
        csv_file = input("Enter the path to your CSV file: ").strip()
        if not csv_file:
            print("[!] No file path provided. Exiting.")
            sys.exit(1)
        
        if not os.path.exists(csv_file):
            print(f"[!] Error: CSV file '{csv_file}' not found!")
            sys.exit(1)
        
        # Check if TextBlob is available
        if not SENTIMENT_AVAILABLE:
            print("[!] TextBlob is required for sentiment analysis. Please install it first.")
            print("Run: pip install textblob")
            print("Then: python -m textblob.download_corpora")
            sys.exit(1)
        
        # Ask for options
        update_csv = input("Update CSV file with sentiment analysis? (y/n): ").strip().lower() == 'y'
        detailed_report = input("Generate detailed report? (y/n): ").strip().lower() == 'y'
        
        print(f"\n[*] Processing CSV file: {csv_file}")
        
        # Update CSV if requested
        if update_csv:
            print("[*] Updating CSV file with sentiment analysis...")
            if not update_csv_with_sentiment(csv_file, backup=True):
                print("[!] Failed to update CSV file with sentiment analysis")
                sys.exit(1)
        
        # Generate report
        print("[*] Generating sentiment analysis report...")
        success = generate_sentiment_report(csv_file, detailed=detailed_report)
        
        if success:
            print("[*] Sentiment analysis completed successfully!")
        else:
            print("[!] Failed to generate sentiment analysis report")
            sys.exit(1)
    else:
        # Run with command line arguments
        main()