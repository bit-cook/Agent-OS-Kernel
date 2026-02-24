"""
Time Window Module

Provides time window functionality including:
- Sliding window: A moving window that slides over a time series
- Fixed window: Fixed time intervals (buckets)
- Window merge: Merging overlapping or adjacent windows
- Window statistics: Computing statistics over windows
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import math


@dataclass
class TimeWindow:
    """Represents a time window with start and end times."""
    start_time: datetime
    end_time: datetime
    data: Any = None
    
    def __post_init__(self):
        if self.end_time < self.start_time:
            raise ValueError("end_time must be >= start_time")
    
    def duration(self) -> timedelta:
        """Return the duration of the window."""
        return self.end_time - self.start_time
    
    def contains(self, timestamp: datetime) -> bool:
        """Check if the window contains the given timestamp."""
        return self.start_time <= timestamp <= self.end_time
    
    def overlaps(self, other: 'TimeWindow') -> bool:
        """Check if this window overlaps with another window."""
        return self.start_time <= other.end_time and other.start_time <= self.end_time
    
    def merge(self, other: 'TimeWindow') -> 'TimeWindow':
        """Merge this window with another, returning the union."""
        if not self.overlaps(other):
            raise ValueError("Cannot merge non-overlapping windows")
        return TimeWindow(
            start_time=min(self.start_time, other.start_time),
            end_time=max(self.end_time, other.end_time),
            data=self.data
        )
    
    def __lt__(self, other: 'TimeWindow') -> bool:
        """Compare windows by start time."""
        return self.start_time < other.start_time
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, TimeWindow):
            return False
        return (self.start_time == other.start_time and 
                self.end_time == other.end_time)


class SlidingWindow:
    """
    A sliding time window that moves over a time series.
    
    Maintains a fixed-size window that slides forward as new data arrives.
    """
    
    def __init__(self, window_size: timedelta, step_size: Optional[timedelta] = None):
        """
        Initialize a sliding window.
        
        Args:
            window_size: The size/duration of each window
            step_size: How far to move the window each step (default: same as window_size)
        """
        self.window_size = window_size
        self.step_size = step_size if step_size else window_size
        self._data: List[Tuple[datetime, Any]] = []
        self._current_window: Optional[TimeWindow] = None
    
    def add(self, timestamp: datetime, value: Any) -> Optional[TimeWindow]:
        """
        Add a data point to the window.
        
        Args:
            timestamp: The timestamp of the data point
            value: The data value
            
        Returns:
            The current window if it was just formed, None otherwise
        """
        self._data.append((timestamp, value))
        self._prune_old_data(timestamp)
        
        if len(self._data) == 0:
            return None
        
        start_times = [t for t, _ in self._data]
        window_start = min(start_times)
        window_end = window_start + self.window_size
        
        if window_end - window_start < self.window_size:
            return None
            
        self._current_window = TimeWindow(
            start_time=window_start,
            end_time=window_end
        )
        return self._current_window
    
    def _prune_old_data(self, current_time: datetime) -> None:
        """Remove data points outside the current window."""
        cutoff = current_time - self.window_size
        self._data = [(t, v) for t, v in self._data if t >= cutoff]
    
    def get_current_window(self) -> Optional[TimeWindow]:
        """Get the current active window."""
        return self._current_window
    
    def get_values_in_window(self) -> List[Any]:
        """Get all values in the current window."""
        if not self._current_window:
            return []
        return [v for t, v in self._data if self._current_window.contains(t)]
    
    def get_data_points(self) -> List[Tuple[datetime, Any]]:
        """Get all data points in the window."""
        return self._data.copy()
    
    def count(self) -> int:
        """Return the number of data points in the window."""
        return len(self._data)
    
    def reset(self) -> None:
        """Reset the window, clearing all data."""
        self._data = []
        self._current_window = None


class FixedWindow:
    """
    A fixed time window (bucket) that accumulates data within a time interval.
    
    Data is grouped into fixed time buckets (e.g., per minute, per hour).
    """
    
    def __init__(self, window_size: timedelta):
        """
        Initialize a fixed window.
        
        Args:
            window_size: The size of each fixed time bucket
        """
        self.window_size = window_size
        self._buckets: Dict[datetime, List[Any]] = defaultdict(list)
        self._bucket_ranges: Dict[datetime, Tuple[datetime, datetime]] = {}
    
    def _get_bucket_key(self, timestamp: datetime) -> datetime:
        """Get the bucket key for a timestamp."""
        return timestamp - (timestamp.timestamp() % self.window_size.total_seconds()) * timedelta(seconds=1)
    
    def add(self, timestamp: datetime, value: Any) -> Tuple[datetime, datetime]:
        """
        Add a data point to the appropriate bucket.
        
        Args:
            timestamp: The timestamp of the data point
            value: The data value
            
        Returns:
            Tuple of (bucket_start, bucket_end) times
        """
        bucket_start = self._get_bucket_key(timestamp)
        bucket_end = bucket_start + self.window_size
        
        if bucket_start not in self._buckets:
            self._bucket_ranges[bucket_start] = (bucket_start, bucket_end)
        
        self._buckets[bucket_start].append(value)
        return (bucket_start, bucket_end)
    
    def get_bucket(self, timestamp: datetime) -> List[Any]:
        """Get all values in the bucket containing the given timestamp."""
        bucket_key = self._get_bucket_key(timestamp)
        return self._buckets.get(bucket_key, [])
    
    def get_all_buckets(self) -> Dict[datetime, List[Any]]:
        """Get all buckets and their values."""
        return dict(self._buckets)
    
    def get_bucket_range(self, timestamp: datetime) -> Optional[Tuple[datetime, datetime]]:
        """Get the time range for the bucket containing the given timestamp."""
        bucket_key = self._get_bucket_key(timestamp)
        return self._bucket_ranges.get(bucket_key)
    
    def get_bucket_counts(self) -> Dict[datetime, int]:
        """Get the count of items in each bucket."""
        return {k: len(v) for k, v in self._buckets.items()}
    
    def count(self, timestamp: Optional[datetime] = None) -> int:
        """Count items in a specific bucket or total."""
        if timestamp is None:
            return sum(len(v) for v in self._buckets.values())
        return len(self.get_bucket(timestamp))
    
    def get_window_for_time(self, timestamp: datetime) -> TimeWindow:
        """Get a TimeWindow for the bucket containing the given timestamp."""
        bucket_key = self._get_bucket_key(timestamp)
        if bucket_key in self._bucket_ranges:
            start, end = self._bucket_ranges[bucket_key]
            return TimeWindow(start_time=start, end_time=end)
        raise ValueError(f"No bucket found for timestamp {timestamp}")
    
    def get_all_windows(self) -> List[TimeWindow]:
        """Get all non-empty windows."""
        windows = []
        for bucket_key in sorted(self._buckets.keys()):
            if self._buckets[bucket_key]:
                start, end = self._bucket_ranges[bucket_key]
                windows.append(TimeWindow(start_time=start, end_time=end))
        return windows
    
    def reset(self) -> None:
        """Reset all buckets."""
        self._buckets.clear()
        self._bucket_ranges.clear()


class WindowMerger:
    """Utility class for merging overlapping or adjacent windows."""
    
    @staticmethod
    def merge_overlapping(windows: List[TimeWindow]) -> List[TimeWindow]:
        """
        Merge a list of overlapping or adjacent windows.
        
        Args:
            windows: List of TimeWindow objects
            
        Returns:
            List of merged (non-overlapping) windows
        """
        if not windows:
            return []
        
        sorted_windows = sorted(windows, key=lambda w: w.start_time)
        merged = [sorted_windows[0]]
        
        for current in sorted_windows[1:]:
            last = merged[-1]
            if current.start_time <= last.end_time:
                # Overlap or adjacent - merge them
                merged[-1] = last.merge(current)
            else:
                # No overlap - add as new window
                merged.append(current)
        
        return merged
    
    @staticmethod
    def merge_by_gap(windows: List[TimeWindow], max_gap: timedelta) -> List[TimeWindow]:
        """
        Merge windows that are within a maximum gap of each other.
        
        Args:
            windows: List of TimeWindow objects
            max_gap: Maximum gap to allow between windows
            
        Returns:
            List of merged windows
        """
        if not windows:
            return []
        
        sorted_windows = sorted(windows, key=lambda w: w.start_time)
        merged = [sorted_windows[0]]
        
        for current in sorted_windows[1:]:
            last = merged[-1]
            gap = current.start_time - last.end_time
            if gap <= max_gap:
                # Gap is small enough - merge
                merged[-1] = TimeWindow(
                    start_time=last.start_time,
                    end_time=max(last.end_time, current.end_time)
                )
            else:
                # Gap is too large - add as new window
                merged.append(current)
        
        return merged
    
    @staticmethod
    def find_gaps(windows: List[TimeWindow]) -> List[TimeWindow]:
        """
        Find the gaps between windows.
        
        Args:
            windows: List of TimeWindow objects
            
        Returns:
            List of TimeWindow objects representing gaps
        """
        if not windows:
            return []
        
        sorted_windows = sorted(windows, key=lambda w: w.start_time)
        gaps = []
        
        for i in range(len(sorted_windows) - 1):
            current_end = sorted_windows[i].end_time
            next_start = sorted_windows[i + 1].start_time
            
            if next_start > current_end:
                gaps.append(TimeWindow(start_time=current_end, end_time=next_start))
        
        return gaps


class WindowStats:
    """Computes statistics over time windows."""
    
    @staticmethod
    def count(windows: List[TimeWindow]) -> int:
        """Count the number of windows."""
        return len(windows)
    
    @staticmethod
    def total_duration(windows: List[TimeWindow]) -> timedelta:
        """Calculate the total duration covered by all windows."""
        if not windows:
            return timedelta(0)
        merged = WindowMerger.merge_overlapping(windows)
        total = timedelta(0)
        for window in merged:
            total += window.duration()
        return total
    
    @staticmethod
    def coverage_ratio(windows: List[TimeWindow], total_span: timedelta) -> float:
        """Calculate the ratio of time covered by windows to total span."""
        if total_span.total_seconds() == 0:
            return 0.0
        covered = WindowStats.total_duration(windows)
        return covered.total_seconds() / total_span.total_seconds()
    
    @staticmethod
    def average_window_size(windows: List[TimeWindow]) -> timedelta:
        """Calculate the average size of windows."""
        if not windows:
            return timedelta(0)
        total = sum(w.duration().total_seconds() for w in windows)
        return timedelta(seconds=total / len(windows))
    
    @staticmethod
    def window_size_stats(windows: List[TimeWindow]) -> Dict[str, float]:
        """Calculate statistics about window sizes."""
        if not windows:
            return {'min': 0, 'max': 0, 'mean': 0, 'median': 0, 'std': 0}
        
        sizes = sorted([w.duration().total_seconds() for w in windows])
        n = len(sizes)
        
        mean = sum(sizes) / n
        min_size = sizes[0]
        max_size = sizes[-1]
        
        if n % 2 == 0:
            median = (sizes[n // 2 - 1] + sizes[n // 2]) / 2
        else:
            median = sizes[n // 2]
        
        variance = sum((s - mean) ** 2 for s in sizes) / n
        std = math.sqrt(variance)
        
        return {
            'min': min_size,
            'max': max_size,
            'mean': mean,
            'median': median,
            'std': std
        }
    
    @staticmethod
    def gap_stats(windows: List[TimeWindow]) -> Dict[str, Any]:
        """Calculate statistics about gaps between windows."""
        gaps = WindowMerger.find_gaps(windows)
        if not gaps:
            return {'count': 0, 'total': 0, 'avg': 0}
        
        gap_sizes = [g.duration().total_seconds() for g in gaps]
        return {
            'count': len(gaps),
            'total': sum(gap_sizes),
            'avg': sum(gap_sizes) / len(gap_sizes),
            'gaps': gaps
        }
    
    @staticmethod
    def overlap_count(windows: List[TimeWindow]) -> int:
        """Count how many windows overlap with at least one other window."""
        if len(windows) < 2:
            return 0
        
        count = 0
        for i, window in enumerate(windows):
            for j, other in enumerate(windows):
                if i != j and window.overlaps(other):
                    count += 1
                    break
        return count
    
    @staticmethod
    def get_summary(windows: List[TimeWindow], total_span: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get a comprehensive summary of window statistics."""
        summary = {
            'count': WindowStats.count(windows),
            'total_duration': WindowStats.total_duration(windows).total_seconds(),
            'average_window_size': WindowStats.average_window_size(windows).total_seconds(),
            'window_size_stats': WindowStats.window_size_stats(windows),
            'gap_stats': WindowStats.gap_stats(windows),
            'overlap_count': WindowStats.overlap_count(windows)
        }
        
        if total_span:
            summary['coverage_ratio'] = WindowStats.coverage_ratio(windows, total_span)
        
        return summary
