"""
Technical Analysis Module
RSI, MACD, Moving Averages, Bollinger Bands, Volume Profile, Trends
"""

import numpy as np
import pandas as pd
from typing import Dict, List
from config import *


class TechnicalAnalysis:
    """Calculate all technical indicators for trading signals"""
    
    def __init__(self):
        self.data = None
        
    def calculate_all_indicators(self, ohlcv_data: List[Dict]) -> Dict:
        """Calculate all technical indicators"""
        try:
            if not ohlcv_data or len(ohlcv_data) < 5:
                return {
                    'indicators': {},
                    'signals': {
                        'buy_confidence': 0,
                        'should_buy': False,
                        'active_signals': 0,
                        'total_signals': 0,
                        'signal_alignment': '0/0'
                    },
                    'current_price': 0,
                    'timestamp': None
                }
            
            df = pd.DataFrame(ohlcv_data)
            
            # Convert to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove NaN values
            df = df.dropna()
            
            if len(df) < 5:
                return {
                    'indicators': {},
                    'signals': {
                        'buy_confidence': 0,
                        'should_buy': False,
                        'active_signals': 0,
                        'total_signals': 0,
                        'signal_alignment': '0/0'
                    },
                    'current_price': df['close'].iloc[-1] if len(df) > 0 else 0,
                    'timestamp': None
                }
            
            indicators = {
                'sma': self.calculate_sma(df),
                'ema': self.calculate_ema(df),
                'rsi': self.calculate_rsi(df),
                'macd': self.calculate_macd(df),
                'bollinger_bands': self.calculate_bollinger_bands(df),
                'volume': self.calculate_volume_profile(df),
                'trend': self.calculate_trend(df),
                'support_resistance': self.calculate_support_resistance(df)
            }
            
            signals = self.generate_signals(indicators, df)
            
            return {
                'indicators': indicators,
                'signals': signals,
                'current_price': float(df['close'].iloc[-1]),
                'timestamp': df['timestamp'].iloc[-1] if 'timestamp' in df else None
            }
        except Exception as e:
            print(f"Error calculating indicators: {e}")
            return {
                'indicators': {},
                'signals': {
                    'buy_confidence': 0,
                    'should_buy': False,
                    'active_signals': 0,
                    'total_signals': 0,
                    'signal_alignment': '0/0'
                },
                'current_price': 0,
                'timestamp': None
            }
    
    def calculate_sma(self, df: pd.DataFrame) -> Dict:
        """Simple Moving Average"""
        try:
            sma_short = df['close'].rolling(window=min(SMA_SHORT, len(df))).mean()
            sma_long = df['close'].rolling(window=min(SMA_LONG, len(df))).mean()
            
            return {
                'sma_short': float(sma_short.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) else 0,
                'sma_long': float(sma_long.iloc[-1]) if not pd.isna(sma_long.iloc[-1]) else 0,
                'bullish': float(sma_short.iloc[-1]) > float(sma_long.iloc[-1]) if not pd.isna(sma_short.iloc[-1]) and not pd.isna(sma_long.iloc[-1]) else False
            }
        except:
            return {'sma_short': 0, 'sma_long': 0, 'bullish': False}
    
    def calculate_ema(self, df: pd.DataFrame) -> Dict:
        """Exponential Moving Average"""
        try:
            ema_short = df['close'].ewm(span=min(EMA_SHORT, len(df)), adjust=False).mean()
            ema_long = df['close'].ewm(span=min(EMA_LONG, len(df)), adjust=False).mean()
            
            return {
                'ema_short': float(ema_short.iloc[-1]) if not pd.isna(ema_short.iloc[-1]) else 0,
                'ema_long': float(ema_long.iloc[-1]) if not pd.isna(ema_long.iloc[-1]) else 0,
                'bullish': float(ema_short.iloc[-1]) > float(ema_long.iloc[-1]) if not pd.isna(ema_short.iloc[-1]) and not pd.isna(ema_long.iloc[-1]) else False
            }
        except:
            return {'ema_short': 0, 'ema_long': 0, 'bullish': False}
    
    def calculate_rsi(self, df: pd.DataFrame) -> Dict:
        """Relative Strength Index"""
        try:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=min(RSI_PERIOD, len(df))).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=min(RSI_PERIOD, len(df))).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            current_rsi = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50
            
            return {
                'value': current_rsi,
                'overbought': current_rsi > RSI_OVERBOUGHT,
                'oversold': current_rsi < RSI_OVERSOLD,
                'buy_signal': RSI_BUY_THRESHOLD < current_rsi < 70,
                'sell_signal': current_rsi > RSI_SELL_THRESHOLD
            }
        except:
            return {'value': 50, 'overbought': False, 'oversold': False, 'buy_signal': False, 'sell_signal': False}
    
    def calculate_macd(self, df: pd.DataFrame) -> Dict:
        """MACD (Moving Average Convergence Divergence)"""
        try:
            ema_12 = df['close'].ewm(span=min(MACD_FAST, len(df)), adjust=False).mean()
            ema_26 = df['close'].ewm(span=min(MACD_SLOW, len(df)), adjust=False).mean()
            
            macd_line = ema_12 - ema_26
            signal_line = macd_line.ewm(span=min(MACD_SIGNAL, len(df)), adjust=False).mean()
            histogram = macd_line - signal_line
            
            current_macd = float(macd_line.iloc[-1]) if not pd.isna(macd_line.iloc[-1]) else 0
            current_signal = float(signal_line.iloc[-1]) if not pd.isna(signal_line.iloc[-1]) else 0
            current_histogram = float(histogram.iloc[-1]) if not pd.isna(histogram.iloc[-1]) else 0
            prev_histogram = float(histogram.iloc[-2]) if len(histogram) > 1 and not pd.isna(histogram.iloc[-2]) else 0
            
            return {
                'macd_line': current_macd,
                'signal_line': current_signal,
                'histogram': current_histogram,
                'bullish_crossover': prev_histogram < 0 and current_histogram > 0,
                'bearish_crossover': prev_histogram > 0 and current_histogram < 0,
                'buy_signal': current_histogram > 0 and current_macd > current_signal
            }
        except:
            return {
                'macd_line': 0,
                'signal_line': 0,
                'histogram': 0,
                'bullish_crossover': False,
                'bearish_crossover': False,
                'buy_signal': False
            }
    
    def calculate_bollinger_bands(self, df: pd.DataFrame) -> Dict:
        """Bollinger Bands"""
        try:
            sma = df['close'].rolling(window=min(BB_PERIOD, len(df))).mean()
            std = df['close'].rolling(window=min(BB_PERIOD, len(df))).std()
            
            upper_band = sma + (BB_STD_DEV * std)
            lower_band = sma - (BB_STD_DEV * std)
            
            current_price = float(df['close'].iloc[-1])
            upper = float(upper_band.iloc[-1]) if not pd.isna(upper_band.iloc[-1]) else current_price
            lower = float(lower_band.iloc[-1]) if not pd.isna(lower_band.iloc[-1]) else current_price
            middle = float(sma.iloc[-1]) if not pd.isna(sma.iloc[-1]) else current_price
            
            return {
                'upper_band': upper,
                'middle_band': middle,
                'lower_band': lower,
                'price_near_lower': current_price < middle,
                'squeeze': (upper - lower) < (middle * 0.05) if middle > 0 else False,
                'buy_signal': current_price < lower
            }
        except:
            return {
                'upper_band': 0,
                'middle_band': 0,
                'lower_band': 0,
                'price_near_lower': False,
                'squeeze': False,
                'buy_signal': False
            }
    
    def calculate_volume_profile(self, df: pd.DataFrame) -> Dict:
        """Volume Analysis"""
        try:
            volume_ma = df['volume'].rolling(window=min(VOLUME_MA_PERIOD, len(df))).mean()
            current_volume = float(df['volume'].iloc[-1])
            avg_volume = float(volume_ma.iloc[-1]) if not pd.isna(volume_ma.iloc[-1]) else current_volume
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0
            
            increasing_volume = current_volume > avg_volume
            
            return {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'increasing': increasing_volume,
                'buy_signal': volume_ratio > MIN_VOLUME_RATIO and increasing_volume
            }
        except:
            return {
                'current_volume': 0,
                'average_volume': 0,
                'volume_ratio': 0,
                'increasing': False,
                'buy_signal': False
            }
    
    def calculate_trend(self, df: pd.DataFrame) -> Dict:
        """Identify trend direction and strength"""
        try:
            if len(df) < 2:
                return {'direction': 'neutral', 'slope': 0, 'strength': 0, 'bullish': False}
            
            closes = df['close'].values.astype(float)
            
            x = np.arange(len(closes))
            z = np.polyfit(x, closes, 1)
            
            slope = float(z[0])
            mean_close = float(np.mean(closes))
            trend_strength = (abs(slope) / mean_close * 100) if mean_close > 0 else 0
            
            return {
                'direction': 'uptrend' if slope > 0 else 'downtrend',
                'slope': slope,
                'strength': trend_strength,
                'bullish': slope > 0
            }
        except:
            return {'direction': 'neutral', 'slope': 0, 'strength': 0, 'bullish': False}
    
    def calculate_support_resistance(self, df: pd.DataFrame, lookback: int = 20) -> Dict:
        """Calculate support and resistance levels"""
        try:
            lookback = min(lookback, len(df))
            high = float(df['high'].tail(lookback).max())
            low = float(df['low'].tail(lookback).min())
            current = float(df['close'].iloc[-1])
            
            resistance = high
            support = low
            pivot = (high + low + current) / 3
            
            return {
                'resistance': resistance,
                'support': support,
                'pivot': pivot,
                'near_resistance': current > (resistance - (resistance - current) * 0.1),
                'near_support': current < (support + (current - support) * 0.1),
                'buy_near_support': current < support * 1.02
            }
        except:
            return {
                'resistance': 0,
                'support': 0,
                'pivot': 0,
                'near_resistance': False,
                'near_support': False,
                'buy_near_support': False
            }
    
    def generate_signals(self, indicators: Dict, df: pd.DataFrame) -> Dict:
        """Generate buy/sell signals"""
        try:
            buy_signals = 0
            total_signals = 7
            
            if indicators.get('rsi', {}).get('buy_signal', False):
                buy_signals += 1
            if indicators.get('macd', {}).get('buy_signal', False):
                buy_signals += 1
            sma_bullish = indicators.get('sma', {}).get('bullish', False)
            ema_bullish = indicators.get('ema', {}).get('bullish', False)
            if sma_bullish and ema_bullish:
                buy_signals += 1
            if indicators.get('bollinger_bands', {}).get('buy_signal', False):
                buy_signals += 1
            if indicators.get('volume', {}).get('buy_signal', False):
                buy_signals += 1
            if indicators.get('trend', {}).get('bullish', False):
                buy_signals += 1
            if indicators.get('support_resistance', {}).get('buy_near_support', False):
                buy_signals += 1
            
            confidence = (buy_signals / total_signals * 100) if total_signals > 0 else 0
            
            return {
                'buy_confidence': confidence,
                'should_buy': confidence >= 60,
                'active_signals': buy_signals,
                'total_signals': total_signals,
                'signal_alignment': f"{buy_signals}/{total_signals}"
            }
        except Exception as e:
            print(f"Error generating signals: {e}")
            return {
                'buy_confidence': 0,
                'should_buy': False,
                'active_signals': 0,
                'total_signals': 0,
                'signal_alignment': '0/0'
            }
