import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import re

def get_biospace_news():
    """Scrape news from BioSpace."""
    url = "https://www.biospace.com/news/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = []
    
    # Find all article elements
    article_elements = soup.find_all('div', class_='article-item')
    
    for article in article_elements[:7]:  # Get top 7 articles
        title_element = article.find('h2', class_='title')
        if not title_element:
            continue
            
        link_element = title_element.find('a')
        if not link_element:
            continue
            
        title = link_element.text.strip()
        url = f"https://www.biospace.com{link_element['href']}"
        
        # Get article content
        article_response = requests.get(url, headers=headers)
        article_soup = BeautifulSoup(article_response.text, 'html.parser')
        content_element = article_soup.find('div', class_='article-content')
        content = content_element.text.strip() if content_element else ""
        
        articles.append({
            'title': title,
            'url': url,
            'content': content
        })
    
    return articles

def categorize_news(articles):
    """Categorize news into sections."""
    categories = {
        "주요 헤드라인": [],
        "산업 동향": [],
        "사업 계약": [],
        "규제 및 정책": []
    }
    
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
    
    return categories

def shorten_url(url):
    """Create shortened URL using TinyURL API."""
    api_key = os.getenv('TINYURL_API_KEY')
    if not api_key:
        return url
        
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    data = {
        'url': url,
        'domain': 'tinyurl.com'
    }
    try:
        response = requests.post('https://api.tinyurl.com/create', 
                               headers=headers, 
                               json=data)
        return response.json()['data']['tiny_url']
    except:
        return url

def extract_key_points(content):
    """Extract key points from article content."""
    sentences = re.split(r'[.!?]+', content)
    key_points = []
    
    for sentence in sentences[:3]:  # Get first 3 meaningful sentences
        sentence = sentence.strip()
        if len(sentence) > 20:  # Only include meaningful sentences
            key_points.append(sentence)
    
    return key_points

def generate_report(categories):
    """Generate the markdown report."""
    kst = pytz.timezone('Asia/Seoul')
    today = datetime.now(kst).strftime('%Y년 %m월 %d일')
    
    report = f"""# 바이오스페이스 일일 뉴스 리포트 - {today}

"""
    
    # Add each section
    for section, articles in categories.items():
        if articles:
            report += f"\n## {section}\n\n"
            
            for i, article in enumerate(articles, 1):
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
    
    report += f"\n---\n*{today} 바이오스페이스 뉴스 피드에서 생성된 리포트*"
    return report

def main():
    # Get news articles
    articles = get_biospace_news()
    
    # Categorize news
    categories = categorize_news(articles)
    
    # Generate report
    report = generate_report(categories)
    
    # Save report
    with open('daily_news_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

if __name__ == "__main__":
    main() 