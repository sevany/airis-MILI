"""
XAUUSD News Sentiment Analyzer
Uses EOD Historical Data News API
"""
import requests
import json
import os
from datetime import datetime, timedelta
from backend.config import Config

class XAUUSDNews:
    """News sentiment analyzer for gold trading"""
    
    BASE_URL = "https://eodhistoricaldata.com/api"
    CACHE_DIR = "./data/xauusd"
    
    # Keywords that affect gold prices
    GOLD_KEYWORDS = [
        'gold', 'xauusd', 'precious metals',
        'federal reserve', 'fed', 'interest rates',
        'inflation', 'cpi', 'pce',
        'dollar', 'usd', 'dxy',
        'treasury', 'bonds', 'yields'
    ]
    
    def __init__(self, api_key=None):
        self.api_key = api_key or Config.EOD_API_KEY
        if not self.api_key:
            raise ValueError("EOD_API_KEY not configured")
        
        os.makedirs(self.CACHE_DIR, exist_ok=True)
    
    def fetch_gold_news(self, days=3):
        """
        Fetch recent gold-related news
        
        Args:
            days: Number of days to look back
            
        Returns:
            list: News articles
        """
        try:
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')
            
            # Try different news endpoints
            # Option 1: General news with GOLD tag
            url = f"{self.BASE_URL}/news"
            params = {
                'api_token': self.api_key,
                't': 'gold',  # Tag instead of 's' search
                'from': start_date,
                'to': end_date,
                'limit': 50,
                'fmt': 'json'
            }
            
            try:
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                articles = response.json()
            except:
                # Option 2: Try without date filters
                params = {
                    'api_token': self.api_key,
                    't': 'gold,xauusd,precious-metals',
                    'limit': 50,
                    'fmt': 'json'
                }
                response = requests.get(url, params=params, timeout=15)
                response.raise_for_status()
                articles = response.json()
            
            # Filter for gold-relevant news
            relevant = []
            for article in articles:
                title = article.get('title', '').lower()
                content = article.get('content', '').lower()
                
                # Check if article mentions gold keywords
                if any(keyword in title or keyword in content for keyword in self.GOLD_KEYWORDS):
                    relevant.append({
                        'title': article.get('title', ''),
                        'content': article.get('content', '')[:500],  # First 500 chars
                        'date': article.get('date', ''),
                        'link': article.get('link', ''),
                        'sentiment': self._analyze_sentiment(title + ' ' + content)
                    })
            
            return relevant
        
        except Exception as e:
            print(f"❌ News fetch error: {str(e)}")
            return []
    
    def _analyze_sentiment(self, text):
        """
        Simple keyword-based sentiment analysis
        
        Returns:
            float: -1 (bearish) to +1 (bullish)
        """
        text = text.lower()
        
        # Bullish keywords for gold
        bullish_words = [
            'surge', 'rally', 'rise', 'gain', 'up', 'bullish', 'strong',
            'inflation', 'uncertainty', 'crisis', 'safe haven',
            'dovish', 'lower rates', 'stimulus', 'weak dollar'
        ]
        
        # Bearish keywords for gold
        bearish_words = [
            'fall', 'drop', 'decline', 'down', 'bearish', 'weak',
            'strong dollar', 'rate hike', 'hawkish', 'tightening',
            'risk-on', 'sell-off'
        ]
        
        bullish_count = sum(1 for word in bullish_words if word in text)
        bearish_count = sum(1 for word in bearish_words if word in text)
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0  # Neutral
        
        # Normalize to -1 to +1
        score = (bullish_count - bearish_count) / total
        return round(score, 2)
    
    def get_sentiment_summary(self):
        """
        Get aggregated sentiment from recent news
        
        Returns:
            dict: Sentiment summary
        """
        articles = self.fetch_gold_news(days=3)
        
        if not articles:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'article_count': 0,
                'summary': 'No recent news available'
            }
        
        # Calculate average sentiment
        scores = [a['sentiment'] for a in articles]
        avg_score = sum(scores) / len(scores)
        
        # Classify sentiment
        if avg_score > 0.2:
            sentiment = 'bullish'
        elif avg_score < -0.2:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'
        
        # Get key headlines
        top_headlines = [a['title'] for a in articles[:5]]
        
        return {
            'sentiment': sentiment,
            'score': round(avg_score, 2),
            'article_count': len(articles),
            'top_headlines': top_headlines,
            'summary': self._generate_summary(sentiment, top_headlines)
        }
    
    def _generate_summary(self, sentiment, headlines):
        """Generate human-readable sentiment summary"""
        sentiment_text = {
            'bullish': 'Positive news flow supporting gold prices',
            'bearish': 'Negative headlines pressuring gold',
            'neutral': 'Mixed news, no clear directional bias'
        }
        
        summary = sentiment_text.get(sentiment, 'Neutral sentiment')
        
        if headlines:
            summary += f". Key themes: {headlines[0][:100]}..."
        
        return summary
    
    def cache_sentiment(self):
        """Cache sentiment analysis"""
        try:
            print("📰 Fetching gold news sentiment...")
            sentiment = self.get_sentiment_summary()
            
            cache_file = os.path.join(self.CACHE_DIR, 'news_cache.json')
            with open(cache_file, 'w') as f:
                json.dump({
                    'updated_at': datetime.now().isoformat(),
                    'sentiment': sentiment
                }, f, indent=2)
            
            print(f"✓ Sentiment: {sentiment['sentiment']} ({sentiment['score']:+.2f})")
            return sentiment
        
        except Exception as e:
            print(f"❌ Cache sentiment error: {str(e)}")
            return None
    
    def load_cached_sentiment(self):
        """Load cached sentiment"""
        cache_file = os.path.join(self.CACHE_DIR, 'news_cache.json')
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Check freshness (< 6 hours)
            updated_at = datetime.fromisoformat(data['updated_at'])
            age_hours = (datetime.now() - updated_at).total_seconds() / 3600
            
            if age_hours < 6:
                print(f"✓ Using cached sentiment (age: {age_hours:.1f}h)")
                return data['sentiment']
            else:
                print(f"⚠️  Sentiment cache stale, refreshing...")
                return None
        
        except Exception as e:
            print(f"❌ Load sentiment cache error: {str(e)}")
            return None