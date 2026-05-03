"""
Technical Indicators Module
Calculate SMA, Bollinger Bands, Support/Resistance for XAUUSD
"""

def calculate_sma(candles, period):
    """Calculate Simple Moving Average"""
    if len(candles) < period:
        return None
    
    closes = [c['close'] for c in candles[:period]]
    return sum(closes) / period

def calculate_bollinger_bands(candles, period=20, std_dev=2):
    """Calculate Bollinger Bands"""
    if len(candles) < period:
        return None, None, None
    
    closes = [c['close'] for c in candles[:period]]
    sma = sum(closes) / period
    
    # Calculate standard deviation
    variance = sum((x - sma) ** 2 for x in closes) / period
    std = variance ** 0.5
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    return upper, sma, lower

def find_support_resistance(candles, lookback=20):
    """Find key support and resistance levels"""
    if len(candles) < lookback:
        return None, None
    
    recent = candles[:lookback]
    highs = [c['high'] for c in recent]
    lows = [c['low'] for c in recent]
    
    resistance = max(highs)
    support = min(lows)
    
    return support, resistance

def determine_trend(candles):
    """Determine trend based on SMA crossovers"""
    if len(candles) < 50:
        return "insufficient_data"
    
    sma_20 = calculate_sma(candles, 20)
    sma_50 = calculate_sma(candles, 50)
    
    if not sma_20 or not sma_50:
        return "insufficient_data"
    
    if sma_20 > sma_50:
        return "bullish"
    elif sma_20 < sma_50:
        return "bearish"
    else:
        return "neutral"

def calculate_pivot_points(yesterday_candle):
    """Calculate pivot points for intraday levels"""
    high = yesterday_candle['high']
    low = yesterday_candle['low']
    close = yesterday_candle['close']
    
    pivot = (high + low + close) / 3
    r1 = (2 * pivot) - low
    s1 = (2 * pivot) - high
    r2 = pivot + (high - low)
    s2 = pivot - (high - low)
    
    return {
        'pivot': round(pivot, 2),
        'r1': round(r1, 2),
        'r2': round(r2, 2),
        's1': round(s1, 2),
        's2': round(s2, 2)
    }

def full_technical_analysis(candles):
    """
    Complete technical analysis on candle data
    
    Args:
        candles: List of OHLC candles (newest first)
        
    Returns:
        dict: Complete analysis
    """
    if len(candles) < 50:
        return {"error": "Insufficient data for analysis"}
    
    # Current price
    current = candles[0]['close']
    
    # Moving averages
    sma_20 = calculate_sma(candles, 20)
    sma_50 = calculate_sma(candles, 50)
    sma_200 = calculate_sma(candles, 200) if len(candles) >= 200 else None
    
    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(candles, 20)
    
    # Support/Resistance
    support, resistance = find_support_resistance(candles, 20)
    
    # Trend
    trend = determine_trend(candles)
    
    # Pivot points
    pivots = calculate_pivot_points(candles[0])
    
    # Price vs key levels
    above_sma20 = current > sma_20 if sma_20 else None
    above_sma50 = current > sma_50 if sma_50 else None
    
    return {
        'current_price': round(current, 2),
        'sma': {
            'sma_20': round(sma_20, 2) if sma_20 else None,
            'sma_50': round(sma_50, 2) if sma_50 else None,
            'sma_200': round(sma_200, 2) if sma_200 else None
        },
        'bollinger_bands': {
            'upper': round(bb_upper, 2) if bb_upper else None,
            'middle': round(bb_middle, 2) if bb_middle else None,
            'lower': round(bb_lower, 2) if bb_lower else None
        },
        'support_resistance': {
            'resistance': round(resistance, 2) if resistance else None,
            'support': round(support, 2) if support else None
        },
        'pivot_points': pivots,
        'trend': trend,
        'position': {
            'above_sma_20': above_sma20,
            'above_sma_50': above_sma50
        }
    }