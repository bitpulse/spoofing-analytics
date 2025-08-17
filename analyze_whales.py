#!/usr/bin/env python3
"""
Correct whale analysis that handles duplicate spoofing issues and provides accurate metrics.

This analyzer:
1. Deduplicates spoofing events (fixes the logging bug)
2. Classifies whales as real vs spoofs based on behavior
3. Calculates true manipulation scores
4. Provides actionable trading insights

Usage:
    python analyze_whales.py [SYMBOL]
    python analyze_whales.py SEIUSDT
    python analyze_whales.py BTCUSDT
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import numpy as np
import sys

def analyze_whales_correctly(symbol="SEIUSDT"):
    """Analyze whale data with proper deduplication"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n{'='*70}")
    print(f"📊 CORRECTED Analysis for {symbol} - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")
    
    # Load data
    whale_file = Path(f"data/whales/{symbol}/{symbol}_whales_{date_str}.csv")
    spoof_file = Path(f"data/spoofing/{symbol}/{symbol}_spoofing_{date_str}.csv")
    
    if not whale_file.exists():
        print("❌ No whale data found")
        return
    
    # Load whale data
    df_whales = pd.read_csv(whale_file)
    print(f"🐋 WHALE DATA ANALYSIS:")
    print(f"  Total whale events logged: {len(df_whales):,}")
    print(f"  Unique whale IDs: {df_whales['whale_id'].nunique()}")
    
    # Group by whale_id to get true whale behavior
    whale_groups = df_whales.groupby('whale_id').agg({
        'value_usd': ['mean', 'max', 'min'],
        'duration_seconds': ['max', 'mean'],
        'timestamp': ['min', 'max', 'count']
    }).round(2)
    
    # Calculate real whale statistics
    avg_whale_value = df_whales.groupby('whale_id')['value_usd'].mean().mean()
    max_whale_value = df_whales['value_usd'].max()
    
    print(f"  Average whale size: ${avg_whale_value:,.0f}")
    print(f"  Largest whale seen: ${max_whale_value:,.0f}")
    
    # Analyze duration patterns
    max_durations = df_whales.groupby('whale_id')['duration_seconds'].max()
    real_whales = max_durations[max_durations > 60].index
    potential_spoofs = max_durations[max_durations <= 60].index
    
    print(f"\n📊 WHALE CLASSIFICATION (by duration):")
    print(f"  Likely REAL whales (>60s): {len(real_whales)} whales")
    print(f"  Potential SPOOFS (<60s): {len(potential_spoofs)} whales")
    
    # Load and deduplicate spoofing data
    actual_spoofs = set()
    if spoof_file.exists():
        df_spoofs = pd.read_csv(spoof_file)
        print(f"\n🚨 SPOOFING DATA (RAW):")
        print(f"  Total spoofing entries: {len(df_spoofs):,} (INFLATED by bug)")
        print(f"  Unique whale IDs marked as spoofs: {df_spoofs['whale_id'].nunique()}")
        
        # Get unique spoofs (deduplicated)
        actual_spoofs = set(df_spoofs['whale_id'].unique())
        
        # Analyze the duplication issue
        spoof_counts = df_spoofs['whale_id'].value_counts()
        avg_duplicates = spoof_counts.mean()
        max_duplicates = spoof_counts.max()
        
        print(f"\n🐛 DATA DUPLICATION ISSUE:")
        print(f"  Average logs per spoof: {avg_duplicates:.0f} (should be 1)")
        print(f"  Maximum logs for one whale: {max_duplicates} (should be 1)")
        print(f"  Duplication factor: {len(df_spoofs) / len(actual_spoofs):.1f}x")
    
    # Calculate CORRECT manipulation score
    unique_whales = df_whales['whale_id'].nunique()
    unique_spoofs = len(actual_spoofs)
    correct_manipulation_score = (unique_spoofs / unique_whales * 100) if unique_whales > 0 else 0
    
    print(f"\n✅ CORRECTED METRICS:")
    print(f"  Unique whales detected: {unique_whales}")
    print(f"  Unique spoofs confirmed: {unique_spoofs}")
    print(f"  TRUE Manipulation Score: {correct_manipulation_score:.1f}%")
    
    # Classify manipulation level correctly
    if correct_manipulation_score < 20:
        level = "🟢 LOW - Safe to trade"
    elif correct_manipulation_score < 50:
        level = "🟡 MODERATE - Trade with caution"
    elif correct_manipulation_score < 80:
        level = "🟠 HIGH - Avoid momentum trades"
    else:
        level = "🔴 EXTREME - Heavy manipulation"
    
    print(f"  Manipulation Level: {level}")
    
    # Analyze actual whale behavior
    print(f"\n🔍 DETAILED WHALE BEHAVIOR:")
    
    # Get whales that are NOT spoofs
    real_whale_ids = set(df_whales['whale_id'].unique()) - actual_spoofs
    df_real = df_whales[df_whales['whale_id'].isin(real_whale_ids)]
    
    if len(df_real) > 0:
        print(f"\n  REAL WHALES ({len(real_whale_ids)} whales):")
        print(f"    Average value: ${df_real['value_usd'].mean():,.0f}")
        print(f"    Average duration: {df_real['duration_seconds'].mean():.1f}s")
        real_events_per_whale = len(df_real) / len(real_whale_ids)
        print(f"    Events per whale: {real_events_per_whale:.1f}")
    
    # Analyze confirmed spoofs
    df_spoofs_only = df_whales[df_whales['whale_id'].isin(actual_spoofs)]
    if len(df_spoofs_only) > 0:
        print(f"\n  CONFIRMED SPOOFS ({len(actual_spoofs)} whales):")
        print(f"    Average value: ${df_spoofs_only['value_usd'].mean():,.0f}")
        print(f"    Average duration: {df_spoofs_only['duration_seconds'].mean():.1f}s")
        spoof_events_per_whale = len(df_spoofs_only) / len(actual_spoofs)
        print(f"    Events per whale: {spoof_events_per_whale:.1f} (flickering)")
    
    # Time-based analysis
    df_whales['timestamp'] = pd.to_datetime(df_whales['timestamp'])
    df_whales['minute'] = df_whales['timestamp'].dt.floor('1min')
    
    # Calculate collection time
    time_span = (df_whales['timestamp'].max() - df_whales['timestamp'].min()).total_seconds() / 60
    
    print(f"\n⏱️ TIME ANALYSIS:")
    print(f"  Data collection span: {time_span:.1f} minutes")
    print(f"  Whales per minute: {unique_whales / max(time_span, 1):.1f}")
    print(f"  Events per minute: {len(df_whales) / max(time_span, 1):.0f}")
    
    # Pattern detection
    print(f"\n🎯 TRADING INSIGHTS:")
    
    if correct_manipulation_score > 80:
        print("  ⚠️ VERY HIGH percentage of whales are spoofing")
        print("  📉 Strategy: Fade all large orders immediately")
        print("  🛑 Risk: HIGH - Use small positions only")
    elif correct_manipulation_score > 50:
        print("  ⚠️ Majority of large orders are fake")
        print("  📊 Strategy: Wait for 60+ second confirmation")
        print("  ⚡ Quick orders (<30s) are likely spoofs")
    else:
        print("  ✅ Reasonable market conditions")
        print("  📈 Strategy: Can follow persistent whales")
        print("  ⏰ Orders lasting >60s are likely real")
    
    # Check for the most active whales
    top_whales = df_whales['whale_id'].value_counts().head(5)
    print(f"\n🏆 MOST ACTIVE WHALES (by event count):")
    for whale_id, count in top_whales.items():
        whale_data = df_whales[df_whales['whale_id'] == whale_id]
        avg_value = whale_data['value_usd'].mean()
        max_duration = whale_data['duration_seconds'].max()
        is_spoof = "🚨 SPOOF" if whale_id in actual_spoofs else "✅ REAL"
        print(f"  {whale_id[:30]}...")
        print(f"    Events: {count}, Avg: ${avg_value:,.0f}, Max duration: {max_duration:.1f}s - {is_spoof}")
    
    return {
        'unique_whales': unique_whales,
        'unique_spoofs': unique_spoofs,
        'manipulation_score': correct_manipulation_score,
        'collection_minutes': time_span
    }

if __name__ == "__main__":
    # Get symbol from command line or use default
    symbol = sys.argv[1] if len(sys.argv) > 1 else "SEIUSDT"
    
    results = analyze_whales_correctly(symbol)
    
    if results:
        print(f"\n{'='*70}")
        print("📝 KEY INSIGHTS:")
        print(f"  • True manipulation score: {results['manipulation_score']:.1f}%")
        print(f"  • Unique whales: {results['unique_whales']}")
        print(f"  • Confirmed spoofs: {results['unique_spoofs']}")
        print(f"  • Data quality: {results['collection_minutes']:.1f} minutes of data")
        print(f"{'='*70}\n")