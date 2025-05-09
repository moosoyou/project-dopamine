import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re
import sys
import traceback
import time

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
        'Connection': 'keep-alive'
    }
    
    try:
        print_debug(f"Fetching URL: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        print_debug(f"Response status: {response.status_code}")
        
        soup = BeautifulSoup(response.text, 'lxml')
        articles = []
        
        # Find all article links - they are direct links with category tags above them
        article_links = soup.find_all('a', href=True)
        article_links = [link for link in article_links if '/business/' in link['href'] or '/policy/' in link['href'] or '/drug-development/' in link['href']]
        
        print_debug(f"Found {len(article_links)} article links")
        
        for idx, link in enumerate(article_links[:7]):  # Get top 7 articles
            try:
                url = link['href']
                if not url.startswith('http'):
                    url = f"https://www.biospace.com{url}"
                
                # Get article content
                print_debug(f"Fetching article: {url}")
                article_response = requests.get(url, headers=headers, timeout=30)
                article_response.raise_for_status()
                article_soup = BeautifulSoup(article_response.text, 'lxml')
                
                # Get title
                title = article_soup.find('h1')
                if not title:
                    print_debug(f"No title found for article {idx}")
                    continue
                title = title.text.strip()
                
                # Get content from article body
                content_element = article_soup.find('div', class_='article-body')
                if not content_element:
                    content_element = article_soup.find('div', class_='body')
                
                content = ""
                if content_element:
                    paragraphs = content_element.find_all('p')
                    content = ' '.join([p.text.strip() for p in paragraphs])
                
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
        if not articles:
            print_debug("No articles were successfully processed")
            return []
            
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
    """Create shortened URL using TinyURL API with caching and error handling."""
    print_debug(f"Shortening URL: {url}")
    
    # Check if we have a cached version
    cache_file = '.url_cache.json'
    url_cache = {}
    
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                url_cache = json.load(f)
                if url in url_cache:
                    print_debug(f"Using cached shortened URL for: {url}")
                    return url_cache[url]
    except Exception as e:
        print_debug(f"Error reading cache: {str(e)}")
    
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
            'domain': 'tinyurl.com',
            'tags': ['biospace', 'news'],
            'expires_at': None  # Never expire
        }
        
        # Add retry logic
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = requests.post(
                    'https://api.tinyurl.com/create',
                    headers=headers,
                    json=data,
                    timeout=30
                )
                response.raise_for_status()
                short_url = response.json()['data']['tiny_url']
                
                # Cache the result
                try:
                    url_cache[url] = short_url
                    with open(cache_file, 'w') as f:
                        json.dump(url_cache, f)
                except Exception as e:
                    print_debug(f"Error caching URL: {str(e)}")
                
                print_debug(f"URL shortened successfully: {short_url}")
                return short_url
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count == max_retries:
                    print_debug(f"Failed to shorten URL after {max_retries} attempts: {str(e)}")
                    return url
                print_debug(f"Retry {retry_count}/{max_retries} for URL shortening")
                time.sleep(1)  # Wait 1 second before retrying
                
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
        
        # Ensure TINYURL_API_KEY is set
        if not os.getenv('TINYURL_API_KEY'):
            print_debug("Warning: TINYURL_API_KEY environment variable not set")
        
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