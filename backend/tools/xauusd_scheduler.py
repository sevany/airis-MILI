"""
XAUUSD Daily Data Scheduler
Runs at 7 AM daily to cache EOD data and news sentiment
"""
import schedule
import time
import json
import os
from datetime import datetime
from backend.tools.xauusd import XAUUSDData
from backend.tools.xauusd_news import XAUUSDNews
from backend.tools.indicators import full_technical_analysis

class XAUUSDScheduler:
    """Daily scheduler for XAUUSD data updates"""
    
    CACHE_DIR = "./data/xauusd"
    
    def __init__(self):
        self.xauusd = XAUUSDData()
        self.news = XAUUSDNews()
        os.makedirs(self.CACHE_DIR, exist_ok=True)
    
    def price_update(self):
        """Quick price update (runs every 15 minutes)"""
        try:
            print(f"💰 Updating XAUUSD price... ({datetime.now().strftime('%H:%M')})")
            
            # Get current price
            current = self.xauusd.get_current_price()
            
            # Update price cache
            cache_file = os.path.join(self.CACHE_DIR, 'current_price.json')
            with open(cache_file, 'w') as f:
                json.dump({
                    'updated_at': datetime.now().isoformat(),
                    'price_data': current
                }, f, indent=2)
            
            print(f"✓ Price: ${current['price']:.2f} ({current['change_percent']:+.2f}%)")
            return current
            
        except Exception as e:
            print(f"❌ Price update error: {str(e)}")
            return None
    
    def daily_update(self):
        """Main daily update job - runs at 7 AM"""
        print("\n" + "="*60)
        print(f"🔔 XAUUSD Daily Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        try:
            # 1. Fetch and cache EOD data
            print("\n1️⃣ Fetching EOD data...")
            candles = self.xauusd.cache_eod_data(days=90)
            
            # 2. Run technical analysis
            print("\n2️⃣ Running technical analysis...")
            ta = full_technical_analysis(candles)
            
            # 3. Fetch and cache news sentiment
            print("\n3️⃣ Analyzing news sentiment...")
            sentiment = self.news.cache_sentiment()
            
            # 4. Generate combined analysis cache
            print("\n4️⃣ Generating trading brief...")
            analysis = {
                'updated_at': datetime.now().isoformat(),
                'technical': ta,
                'sentiment': sentiment,
                'current_price': self.xauusd.get_current_price()
            }
            
            # Save combined analysis
            cache_file = os.path.join(self.CACHE_DIR, 'daily_analysis.json')
            with open(cache_file, 'w') as f:
                json.dump(analysis, f, indent=2)
            
            print(f"\n✅ Daily update complete!")
            print(f"📊 Price: ${analysis['current_price']['price']:.2f}")
            print(f"📈 Trend: {ta['trend']}")
            print(f"📰 Sentiment: {sentiment['sentiment'] if sentiment else 'N/A'}")
            print("="*60 + "\n")
            
            return analysis
        
        except Exception as e:
            print(f"\n❌ Daily update failed: {str(e)}")
            print("="*60 + "\n")
            return None
    
    def manual_update(self):
        """Trigger update manually (for testing)"""
        print("🔧 Manual update triggered...")
        return self.daily_update()
    
    def start_scheduler(self):
        """Start the scheduler (runs in background)"""
        # Schedule daily full update at 9:00 AM
        schedule.every().day.at("09:00").do(self.daily_update)
        
        # Schedule price updates every 15 minutes
        schedule.every(15).minutes.do(self.price_update)
        
        print("⏰ XAUUSD Scheduler started")
        print("📅 Daily full updates: 9:00 AM")
        print("💰 Price updates: Every 15 minutes")
        print("🔄 Running initial updates now...")
        
        # Run both immediately
        self.daily_update()
        self.price_update()
        
        # Keep running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_once(self):
        """Run update once and exit (for cron jobs)"""
        return self.daily_update()

# For standalone execution
if __name__ == "__main__":
    scheduler = XAUUSDScheduler()
    scheduler.run_once()