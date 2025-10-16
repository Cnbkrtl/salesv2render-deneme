"""
Cost Matching Monitoring & Statistics
Tracks match performance across all 7 layers
"""
from typing import Dict, List, Optional
from datetime import datetime
from collections import defaultdict, Counter
import logging

logger = logging.getLogger(__name__)


class CostMatchMonitor:
    """
    Monitors cost matching performance in real-time
    Provides statistics and alerts for optimization
    """
    
    def __init__(self):
        self.reset_stats()
        
    def reset_stats(self):
        """Reset all statistics"""
        self.stats = {
            'total_items': 0,
            'cache_hits': 0,
            'direct_match': 0,
            'base_sku_match': 0,
            'byk_prefix_match': 0,
            'barcode_match': 0,
            'sku_normalize_match': 0,
            'fallback': 0,
            'errors': 0
        }
        
        # BYK prefix statistics (which prefix matched how many times)
        self.byk_prefix_stats = Counter()
        
        # SKU patterns that failed to match
        self.unmatched_patterns = defaultdict(int)
        
        # Fallback items (for analysis)
        self.fallback_items = []
        
        # Timing statistics
        self.timings = {
            'cache': [],
            'direct': [],
            'base_sku': [],
            'byk_prefix': [],
            'barcode': [],
            'normalize': [],
            'total': []
        }
        
        self.session_start = datetime.now()
        
    def record_match(self, method: str, sku: str, matched_sku: Optional[str] = None, 
                    duration_ms: float = 0.0, prefix: Optional[str] = None):
        """
        Record a successful match
        
        Args:
            method: Match method used (cache, direct, base_sku, byk_prefix, etc.)
            sku: Original SKU
            matched_sku: SKU that was matched (if different)
            duration_ms: Time taken in milliseconds
            prefix: BYK prefix used (if applicable)
        """
        self.stats['total_items'] += 1
        
        if method == 'cache':
            self.stats['cache_hits'] += 1
            self.timings['cache'].append(duration_ms)
        elif method == 'direct':
            self.stats['direct_match'] += 1
            self.timings['direct'].append(duration_ms)
        elif method == 'base_sku':
            self.stats['base_sku_match'] += 1
            self.timings['base_sku'].append(duration_ms)
        elif method == 'byk_prefix':
            self.stats['byk_prefix_match'] += 1
            self.timings['byk_prefix'].append(duration_ms)
            if prefix:
                self.byk_prefix_stats[prefix] += 1
        elif method == 'barcode':
            self.stats['barcode_match'] += 1
            self.timings['barcode'].append(duration_ms)
        elif method == 'normalize':
            self.stats['sku_normalize_match'] += 1
            self.timings['normalize'].append(duration_ms)
        elif method == 'fallback':
            self.stats['fallback'] += 1
            self.fallback_items.append({
                'sku': sku,
                'timestamp': datetime.now()
            })
            
    def record_error(self, sku: str, error: str):
        """Record a matching error"""
        self.stats['errors'] += 1
        logger.warning(f"❌ Match error for {sku}: {error}")
        
    def record_unmatched(self, sku: str):
        """Record an unmatched SKU pattern"""
        # Extract pattern (first 3 parts of SKU)
        parts = sku.split('-')
        if len(parts) >= 3:
            pattern = '-'.join(parts[:3])
        else:
            pattern = sku
        self.unmatched_patterns[pattern] += 1
        
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        total = self.stats['total_items']
        if total == 0:
            return {'error': 'No data yet'}
            
        # Calculate non-cache matches
        non_cache = total - self.stats['cache_hits']
        
        return {
            'total_items': total,
            'cache_hit_rate': f"{(self.stats['cache_hits'] / total * 100):.1f}%",
            'real_cost_rate': f"{((total - self.stats['fallback']) / total * 100):.1f}%",
            'fallback_rate': f"{(self.stats['fallback'] / total * 100):.1f}%",
            'layer_breakdown': {
                'cache': f"{self.stats['cache_hits']} ({self.stats['cache_hits'] / total * 100:.1f}%)",
                'direct': f"{self.stats['direct_match']} ({self.stats['direct_match'] / total * 100:.2f}%)" if non_cache > 0 else "0 (0%)",
                'base_sku': f"{self.stats['base_sku_match']} ({self.stats['base_sku_match'] / total * 100:.1f}%)" if non_cache > 0 else "0 (0%)",
                'byk_prefix': f"{self.stats['byk_prefix_match']} ({self.stats['byk_prefix_match'] / total * 100:.1f}%)" if non_cache > 0 else "0 (0%)",
                'barcode': f"{self.stats['barcode_match']} ({self.stats['barcode_match'] / total * 100:.2f}%)" if non_cache > 0 else "0 (0%)",
                'normalize': f"{self.stats['sku_normalize_match']} ({self.stats['sku_normalize_match'] / total * 100:.2f}%)" if non_cache > 0 else "0 (0%)",
                'fallback': f"{self.stats['fallback']} ({self.stats['fallback'] / total * 100:.1f}%)"
            },
            'top_byk_prefixes': self.byk_prefix_stats.most_common(5),
            'session_duration': str(datetime.now() - self.session_start).split('.')[0],
            'errors': self.stats['errors']
        }
        
    def get_alerts(self) -> List[str]:
        """Get alerts for potential issues"""
        alerts = []
        total = self.stats['total_items']
        
        if total == 0:
            return alerts
            
        # Alert if fallback rate is high
        fallback_rate = self.stats['fallback'] / total * 100
        if fallback_rate > 15:
            alerts.append(f"⚠️ HIGH FALLBACK RATE: {fallback_rate:.1f}% (target: <15%)")
            
        # Alert if cache hit rate is low (after first run)
        cache_rate = self.stats['cache_hits'] / total * 100
        if total > 1000 and cache_rate < 90:
            alerts.append(f"⚠️ LOW CACHE HIT RATE: {cache_rate:.1f}% (expected: >95%)")
            
        # Alert if barcode matching is not being used
        if self.stats['barcode_match'] == 0 and total > 100:
            alerts.append("💡 BARCODE MATCHING NOT USED - Consider enabling barcode enrichment")
            
        # Alert if errors are present
        if self.stats['errors'] > 0:
            error_rate = self.stats['errors'] / total * 100
            alerts.append(f"❌ ERRORS DETECTED: {self.stats['errors']} ({error_rate:.2f}%)")
            
        # Alert about most problematic SKU patterns
        if self.unmatched_patterns:
            top_pattern, count = max(self.unmatched_patterns.items(), key=lambda x: x[1])
            if count > 10:
                alerts.append(f"🔍 TOP UNMATCHED PATTERN: {top_pattern} ({count} items)")
                
        return alerts
        
    def print_report(self):
        """Print a formatted monitoring report"""
        summary = self.get_summary()
        alerts = self.get_alerts()
        
        print("\n" + "="*80)
        print("📊 COST MATCHING MONITOR - LIVE STATISTICS")
        print("="*80)
        
        print(f"\n📈 OVERVIEW:")
        print(f"  Total Items Processed: {summary['total_items']:,}")
        print(f"  Real Cost Usage: {summary['real_cost_rate']} ✅")
        print(f"  Fallback Usage: {summary['fallback_rate']} {'⚠️' if float(summary['fallback_rate'].rstrip('%')) > 15 else '✅'}")
        print(f"  Cache Hit Rate: {summary['cache_hit_rate']}")
        print(f"  Session Duration: {summary['session_duration']}")
        
        print(f"\n🎯 LAYER BREAKDOWN:")
        for layer, stat in summary['layer_breakdown'].items():
            emoji = {
                'cache': '💾',
                'direct': '🎯',
                'base_sku': '📦',
                'byk_prefix': '🔤',
                'barcode': '🏷️',
                'normalize': '🔄',
                'fallback': '⚠️'
            }.get(layer, '•')
            print(f"  {emoji} {layer.replace('_', ' ').title()}: {stat}")
            
        if summary.get('top_byk_prefixes'):
            print(f"\n🔝 TOP BYK PREFIXES:")
            for prefix, count in summary['top_byk_prefixes']:
                pct = count / self.stats['byk_prefix_match'] * 100 if self.stats['byk_prefix_match'] > 0 else 0
                print(f"  • {prefix}: {count:,} matches ({pct:.1f}%)")
                
        if alerts:
            print(f"\n⚠️ ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print(f"\n✅ No alerts - all metrics healthy!")
            
        print("\n" + "="*80)
        
    def export_stats(self) -> Dict:
        """Export statistics for logging or storage"""
        return {
            'timestamp': datetime.now().isoformat(),
            'summary': self.get_summary(),
            'alerts': self.get_alerts(),
            'byk_prefix_distribution': dict(self.byk_prefix_stats),
            'unmatched_patterns': dict(self.unmatched_patterns.most_common(20)),
            'fallback_items_sample': self.fallback_items[:50]  # First 50
        }


# Global monitor instance
_monitor = None

def get_monitor() -> CostMatchMonitor:
    """Get or create the global monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = CostMatchMonitor()
    return _monitor

def reset_monitor():
    """Reset the global monitor"""
    global _monitor
    _monitor = CostMatchMonitor()
    return _monitor
