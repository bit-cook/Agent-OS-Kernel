#!/usr/bin/env python3
"""
Log Analyzer - Real-time log file monitoring and analysis tool
"""

import os
import re
import time
from datetime import datetime
from collections import Counter, defaultdict


class LogAnalyzer:
    """Analyze log files and provide real-time insights"""
    
    def __init__(self, log_file=None):
        self.log_file = log_file
        self.log_patterns = {
            'error': r'(ERROR|error|Error|CRITICAL|FATAL)',
            'warning': r'(WARNING|Warning|warning|WARN)',
            'info': r'(INFO|info|Information)',
            'debug': r'(DEBUG|Debug|debug)',
            'http': r'(\d{3})',  # HTTP status codes
            'ip': r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
        }
        self.stats = {
            'total_lines': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'debug': 0,
            'http_responses': Counter(),
            'unique_ips': set(),
            'timestamp_counts': Counter(),
        }
    
    def load_log_file(self, log_file):
        """Load and analyze a log file"""
        if not os.path.exists(log_file):
            return {"error": f"Log file not found: {log_file}"}
        
        self.log_file = log_file
        return self.analyze()
    
    def analyze_line(self, line):
        """Analyze a single log line"""
        self.stats['total_lines'] += 1
        
        # Count log levels
        for level, pattern in [('errors', 'error'), ('warnings', 'warning'), 
                               ('info', 'info'), ('debug', 'debug')]:
            if re.search(self.log_patterns[level], line):
                self.stats[level] += 1
        
        # Extract HTTP status codes
        http_matches = re.findall(self.log_patterns['http'], line)
        for code in http_matches:
            if 100 <= int(code) < 600:
                self.stats['http_responses'][code] += 1
        
        # Extract IP addresses
        ip_matches = re.findall(self.log_patterns['ip'], line)
        for ip in ip_matches:
            self.stats['unique_ips'].add(ip)
        
        # Extract timestamps (basic pattern)
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}|\d{2}/\w{3}/\d{4})', line)
        if timestamp_match:
            self.stats['timestamp_counts'][timestamp_match.group(1)] += 1
    
    def analyze(self):
        """Analyze the entire log file"""
        if not self.log_file or not os.path.exists(self.log_file):
            return {"error": "No log file specified or file not found"}
        
        self.stats = {
            'total_lines': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
            'debug': 0,
            'http_responses': {},
            'unique_ips': list(self.stats['unique_ips']),
            'timestamp_counts': {},
            'file': self.log_file,
            'analyzed_at': datetime.now().isoformat()
        }
        
        with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                self.analyze_line(line)
        
        # Convert sets and Counters to serializable types
        self.stats['unique_ips'] = list(self.stats['unique_ips'])
        self.stats['http_responses'] = dict(self.stats['http_responses'])
        self.stats['timestamp_counts'] = dict(self.stats['timestamp_counts'])
        
        return self.stats
    
    def get_summary(self):
        """Get a summary of the analysis"""
        stats = self.analyze()
        if 'error' in stats:
            return stats
        
        return {
            "file": stats['file'],
            "total_lines": stats['total_lines'],
            "log_levels": {
                "errors": stats['errors'],
                "warnings": stats['warnings'],
                "info": stats['info'],
                "debug": stats['debug'],
            },
            "error_rate": round(stats['errors'] / max(stats['total_lines'], 1) * 100, 2),
            "unique_ips_count": len(stats['unique_ips']),
            "http_responses": dict(sorted(stats['http_responses'].items())),
            "top_timestamps": dict(stats['timestamp_counts'].most_common(10)),
            "analyzed_at": stats['analyzed_at']
        }


def main():
    """CLI interface for log analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Log Analyzer Tool')
    parser.add_argument('log_file', nargs='?', help='Path to log file')
    parser.add_argument('--full', action='store_true', help='Show full statistics')
    parser.add_argument('--summary', action='store_true', help='Show summary only')
    
    args = parser.parse_args()
    
    if not args.log_file:
        print("Usage: python log_analyzer.py <log_file> [--summary]")
        return
    
    analyzer = LogAnalyzer(args.log_file)
    
    if args.summary:
        result = analyzer.get_summary()
    else:
        result = analyzer.analyze()
    
    import json
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
