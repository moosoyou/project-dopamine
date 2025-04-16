import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import sys
import traceback

def print_debug(msg):
    """Print debug message with timestamp."""
    print(f"[DEBUG] {datetime.now().isoformat()}: {msg}", flush=True)

def get_biospace_news():
    """Scrape news from BioSpace."""
    print_debug("Starting news scraping")
    url = "https://www.biospace.com/news/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    
    try:
        print_debug(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print_debug(f"Response status: {response.status_code}")
        
        # Debug: Print the first 500 characters of the response
        print_debug(f"Response preview: {response.text[:500]}")
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Debug: Print all available class names in the HTML
        classes = set()
        for tag in soup.find_all(class_=True):
            classes.update(tag['class'])
        print_debug(f"Available classes: {classes}")
        
        # Try different selectors
        article_elements = []
        selectors = [
            'div.article-item',
            'article',
            '.article',
            '.news-item',
            '.post',
            'div.article-list-item'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                print_debug(f"Found {len(elements)} articles using selector: {selector}")
                article_elements = elements
                break
        
        if not article_elements:
            print_debug("No articles found with any selector")
            # Try direct URL to recent news
            alt_url = "https://www.biospace.com/news/recent/"
            print_debug(f"Trying alternative URL: {alt_url}")
            response = requests.get(alt_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            article_elements = soup.select('div.article-item') or soup.select('article')
        
        print_debug(f"Found {len(article_elements)} articles")
        articles = []
        
        for idx, article in enumerate(article_elements[:7]):  # Get top 7 articles
            try:
                # Try multiple selectors for title
                title_element = (
                    article.find('h2', class_='title') or
                    article.find('h2') or
                    article.find('h3') or
                    article.find(class_='title')
                )
                
                if not title_element:
                    print_debug(f"No title found for article {idx}")
                    continue
                
                # Try multiple ways to get the link
                link_element = (
                    title_element.find('a') or
                    article.find('a', class_='title') or
                    article.find('a')
                )
                
                if not link_element:
                    print_debug(f"No link found for article {idx}")
                    continue
                
                title = link_element.text.strip()
                url = link_element.get('href', '')
                if not url.startswith('http'):
                    url = f"https://www.biospace.com{url}"
                print_debug(f"Processing article: {title}")
                
                # Get article content
                article_response = requests.get(url, headers=headers, timeout=30)
                article_response.raise_for_status()
                article_soup = BeautifulSoup(article_response.text, 'lxml')
                
                # Try multiple selectors for content
                content_element = (
                    article_soup.find('div', class_='article-content') or
                    article_soup.find('div', class_='content') or
                    article_soup.find(class_='post-content')
                )
                
                content = content_element.text.strip() if content_element else ""
                
                if not content:
                    print_debug(f"No content found for article: {title}")
                    content = "Article content not available"
                
                articles.append({
                    'title': title,
                    'url': url,
                    'content': content
                })
                print_debug(f"Successfully processed article: {title}")
            
            except Exception as e:
                print_debug(f"Error processing article {idx}: {str(e)}")
                traceback.print_exc()
                continue
        
        print_debug(f"Successfully processed {len(articles)} articles")
        return articles
        
    except Exception as e:
        print_debug(f"Error in get_biospace_news: {str(e)}")
        traceback.print_exc()
        return []

def categorize_news(articles):
    """Categorize news into sections."""
    print_debug("Starting news categorization")
    categories = {
        "주요 헤드라인": [],
        "산업 동향": [],
        "사업 계약": [],
        "규제 및 정책": []
    }
    
    try:
        for article in articles:
            content = article['content'].lower()
            title = article['title'].lower()
            
            # Categorization logic
            if any(word in content for word in ['phase', 'trial', 'fda', 'approval']):
                categories["주요 헤드라인"].append(article)
            elif any(word in content for word in ['revenue', 'earnings', 'market', 'sales']):
                categories["산업 동향"].append(article)
            elif any(word in content for word in ['deal', 'agreement', 'partnership', 'collaboration']):
                categories["사업 계약"].append(article)
            elif any(word in content for word in ['regulation', 'policy', 'government', 'legislation']):
                categories["규제 및 정책"].append(article)
            else:
                categories["주요 헤드라인"].append(article)
        
        print_debug("News categorization completed")
        return categories
        
    except Exception as e:
        print_debug(f"Error in categorize_news: {str(e)}")
        traceback.print_exc()
        return categories

def shorten_url(url):
    """Create shortened URL using TinyURL API."""
    print_debug(f"Shortening URL: {url}")
    api_key = os.getenv('TINYURL_API_KEY')
    if not api_key:
        print_debug("No TinyURL API key found")
        return url
        
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'url': url,
            'domain': 'tinyurl.com'
        }
        response = requests.post('https://api.tinyurl.com/create', 
                               headers=headers, 
                               json=data,
                               timeout=30)
        response.raise_for_status()
        short_url = response.json()['data']['tiny_url']
        print_debug(f"URL shortened successfully: {short_url}")
        return short_url
    except Exception as e:
        print_debug(f"Error shortening URL: {str(e)}")
        traceback.print_exc()
        return url

def extract_key_points(content):
    """Extract key points from article content."""
    try:
        sentences = re.split(r'[.!?]+', content)
        key_points = []
        
        for sentence in sentences[:3]:  # Get first 3 meaningful sentences
            sentence = sentence.strip()
            if len(sentence) > 20:  # Only include meaningful sentences
                key_points.append(sentence)
        
        return key_points
    except Exception as e:
        print_debug(f"Error extracting key points: {str(e)}")
        traceback.print_exc()
        return ["Content not available"]

def generate_report(categories):
    """Generate the markdown report."""
    print_debug("Starting report generation")
    try:
        kst = pytz.timezone('Asia/Seoul')
        today = datetime.now(kst).strftime('%Y년 %m월 %d일')
        
        report = f"""# 바이오스페이스 일일 뉴스 리포트 - {today}

"""
        
        # Add each section
        for section, articles in categories.items():
            if articles:
                report += f"\n## {section}\n\n"
                
                for i, article in enumerate(articles, 1):
                    try:
                        # Extract company name or main entity from title
                        title_parts = article['title'].split(':')
                        main_entity = title_parts[0].strip()
                        
                        # Extract keywords
                        keywords = []
                        content_lower = article['content'].lower()
                        if 'phase' in content_lower or 'trial' in content_lower:
                            keywords.append('임상')
                        if 'million' in content_lower or 'billion' in content_lower:
                            keywords.append('투자')
                        if 'fda' in content_lower:
                            keywords.append('FDA')
                        if 'deal' in content_lower or 'agreement' in content_lower:
                            keywords.append('계약')
                        
                        # Format keywords
                        keywords_str = ' '.join([f'#{kw}' for kw in keywords]) if keywords else '#뉴스'
                        
                        # Get key points
                        key_points = extract_key_points(article['content'])
                        
                        # Create article entry
                        report += f"{i}. **{main_entity} ({keywords_str})**\n"
                        for point in key_points:
                            report += f"   - {point}\n"
                        
                        # Add shortened URL
                        short_url = shorten_url(article['url'])
                        report += f"   <{short_url}>\n\n"
                    except Exception as e:
                        print_debug(f"Error processing article in report: {str(e)}")
                        traceback.print_exc()
                        continue
        
        report += f"\n---\n*{today} 바이오스페이스 뉴스 피드에서 생성된 리포트*"
        print_debug("Report generation completed")
        return report
        
    except Exception as e:
        print_debug(f"Error in generate_report: {str(e)}")
        traceback.print_exc()
        return f"# Error Generating Report\n\nAn error occurred while generating the report: {str(e)}"

def main():
    try:
        print_debug("Starting main process")
        
        # Get news articles
        articles = get_biospace_news()
        if not articles:
            print_debug("No articles found")
            sys.exit(1)
        
        # Categorize news
        categories = categorize_news(articles)
        
        # Generate report
        report = generate_report(categories)
        
        # Save report
        print_debug("Saving report to file")
        with open('daily_news_report.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print_debug("Report saved successfully")
        
    except Exception as e:
        print_debug(f"Error in main: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 