#!/usr/bin/env python3
"""
Analyze whale and spoofing data per trading pair
"""
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import sys


def analyze_symbol_data(symbol: str, date_str: str = None):
    """Analyze data for a specific symbol"""
    
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    base_dir = Path("data")
    
    # Load whale data
    whale_file = base_dir / "whales" / symbol / f"{symbol}_whales_{date_str}.csv"
    spoof_file = base_dir / "spoofing" / symbol / f"{symbol}_spoofing_{date_str}.csv"
    
    results = {
        'symbol': symbol,
        'date': date_str,
        'whale_stats': {},
        'spoof_stats': {},
        'manipulation_score': 0
    }
    
    # Analyze whale data
    if whale_file.exists():
        df_whales = pd.read_csv(whale_file)
        if not df_whales.empty:
            results['whale_stats'] = {
                'total_events': len(df_whales),
                'unique_whales': df_whales['whale_id'].nunique() if 'whale_id' in df_whales else 0,
                'avg_value_usd': df_whales['value_usd'].mean() if 'value_usd' in df_whales else 0,
                'max_value_usd': df_whales['value_usd'].max() if 'value_usd' in df_whales else 0,
                'avg_duration': df_whales['duration_seconds'].mean() if 'duration_seconds' in df_whales else 0,
                'events_per_whale': len(df_whales) / max(df_whales['whale_id'].nunique(), 1) if 'whale_id' in df_whales else 0
            }
    
    # Analyze spoofing data
    if spoof_file.exists():
        df_spoofs = pd.read_csv(spoof_file)
        if not df_spoofs.empty:
            results['spoof_stats'] = {
                'total_spoofs': len(df_spoofs),
                'unique_spoofers': df_spoofs['whale_id'].nunique() if 'whale_id' in df_spoofs else 0,
                'avg_time_active': df_spoofs['time_active_seconds'].mean() if 'time_active_seconds' in df_spoofs else 0,
                'flickering_count': len(df_spoofs[df_spoofs['spoof_pattern'] == 'flickering']) if 'spoof_pattern' in df_spoofs else 0,
                'avg_disappearances': df_spoofs['disappearances'].mean() if 'disappearances' in df_spoofs else 0,
                'max_disappearances': df_spoofs['disappearances'].max() if 'disappearances' in df_spoofs else 0
            }
            
            # Calculate manipulation score (0-100)
            if results['whale_stats']:
                spoof_ratio = results['spoof_stats']['total_spoofs'] / max(results['whale_stats']['total_events'], 1)
                results['manipulation_score'] = min(spoof_ratio * 100, 100)
    
    return results


def print_analysis(results):
    """Pretty print analysis results"""
    
    print(f"\n{'='*60}")
    print(f"📊 Analysis for {results['symbol']} - {results['date']}")
    print(f"{'='*60}")
    
    if results['whale_stats']:
        print("\n🐋 WHALE STATISTICS:")
        print(f"  Total Events: {results['whale_stats']['total_events']:,}")
        print(f"  Unique Whales: {results['whale_stats']['unique_whales']}")
        print(f"  Events per Whale: {results['whale_stats']['events_per_whale']:.1f}")
        print(f"  Average Value: ${results['whale_stats']['avg_value_usd']:,.0f}")
        print(f"  Max Value: ${results['whale_stats']['max_value_usd']:,.0f}")
        print(f"  Avg Duration: {results['whale_stats']['avg_duration']:.2f} seconds")
    
    if results['spoof_stats']:
        print("\n🚨 SPOOFING STATISTICS:")
        print(f"  Total Spoofs: {results['spoof_stats']['total_spoofs']:,}")
        print(f"  Unique Spoofers: {results['spoof_stats']['unique_spoofers']}")
        print(f"  Avg Time Active: {results['spoof_stats']['avg_time_active']:.2f} seconds")
        print(f"  Flickering Events: {results['spoof_stats']['flickering_count']}")
        print(f"  Avg Disappearances: {results['spoof_stats']['avg_disappearances']:.1f}")
        print(f"  Max Disappearances: {results['spoof_stats']['max_disappearances']}")
    
    print(f"\n🎯 MANIPULATION SCORE: {results['manipulation_score']:.1f}/100")
    
    if results['manipulation_score'] > 80:
        print("  ⚠️ EXTREME MANIPULATION - Avoid trading")
    elif results['manipulation_score'] > 50:
        print("  ⚠️ HIGH MANIPULATION - Trade with caution")
    elif results['manipulation_score'] > 20:
        print("  ⚡ MODERATE MANIPULATION - Some spoofing present")
    else:
        print("  ✅ LOW MANIPULATION - Relatively clean")


def compare_symbols(date_str: str = None):
    """Compare all symbols for the given date"""
    
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    base_dir = Path("data/whales")
    symbols = []
    
    # Find all symbols with data
    if base_dir.exists():
        for symbol_dir in base_dir.iterdir():
            if symbol_dir.is_dir():
                symbols.append(symbol_dir.name)
    
    if not symbols:
        print("No data found!")
        return
    
    print(f"\n{'='*80}")
    print(f"📊 COMPARATIVE ANALYSIS - {date_str}")
    print(f"{'='*80}")
    
    all_results = []
    for symbol in sorted(symbols):
        results = analyze_symbol_data(symbol, date_str)
        all_results.append(results)
    
    # Sort by manipulation score
    all_results.sort(key=lambda x: x['manipulation_score'], reverse=True)
    
    print("\n🏆 MANIPULATION RANKING (Most to Least):\n")
    print(f"{'Symbol':<10} {'Whale Events':<15} {'Spoofs':<10} {'Manipulation':<15} {'Status'}")
    print("-" * 70)
    
    for r in all_results:
        whales = r['whale_stats'].get('total_events', 0)
        spoofs = r['spoof_stats'].get('total_spoofs', 0)
        score = r['manipulation_score']
        
        if score > 80:
            status = "🔴 EXTREME"
        elif score > 50:
            status = "🟠 HIGH"
        elif score > 20:
            status = "🟡 MODERATE"
        else:
            status = "🟢 LOW"
        
        print(f"{r['symbol']:<10} {whales:<15,} {spoofs:<10,} {score:<15.1f} {status}")
    
    # Summary statistics
    print(f"\n📈 TOTALS:")
    total_whales = sum(r['whale_stats'].get('total_events', 0) for r in all_results)
    total_spoofs = sum(r['spoof_stats'].get('total_spoofs', 0) for r in all_results)
    print(f"  Total Whale Events: {total_whales:,}")
    print(f"  Total Spoofing Events: {total_spoofs:,}")
    print(f"  Overall Spoof Rate: {(total_spoofs/max(total_whales,1)*100):.1f}%")


def main():
    """Main entry point"""
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "compare":
            # Compare all symbols
            date_str = sys.argv[2] if len(sys.argv) > 2 else None
            compare_symbols(date_str)
        else:
            # Analyze specific symbol
            symbol = sys.argv[1].upper()
            date_str = sys.argv[2] if len(sys.argv) > 2 else None
            results = analyze_symbol_data(symbol, date_str)
            print_analysis(results)
    else:
        print("\nUsage:")
        print("  python analyze_data.py SYMBOL [DATE]     # Analyze specific symbol")
        print("  python analyze_data.py compare [DATE]    # Compare all symbols")
        print("\nExample:")
        print("  python analyze_data.py ARBUSDT")
        print("  python analyze_data.py ARBUSDT 2025-08-15")
        print("  python analyze_data.py compare")
        print("  python analyze_data.py compare 2025-08-15")


if __name__ == "__main__":
    main()