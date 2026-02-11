"""URL Checker Tool Module"""

import requests
from typing import List, Dict, Tuple


def check_url(url: str, timeout: int = 10) -> Dict[str, any]:
    """
    Check if a URL is accessible.
    
    Args:
        url: The URL to check
        timeout: Request timeout in seconds
    
    Returns:
        Dictionary with status, url, and response_time
    """
    try:
        response = requests.get(url, timeout=timeout)
        return {
            "url": url,
            "status": response.status_code,
            "accessible": response.status_code < 400,
            "response_time": response.elapsed.total_seconds()
        }
    except requests.exceptions.Timeout:
        return {
            "url": url,
            "status": "timeout",
            "accessible": False,
            "response_time": timeout
        }
    except requests.exceptions.RequestException as e:
        return {
            "url": url,
            "status": "error",
            "error": str(e),
            "accessible": False,
            "response_time": None
        }


def check_urls(urls: List[str], timeout: int = 10) -> List[Dict[str, any]]:
    """
    Check multiple URLs.
    
    Args:
        urls: List of URLs to check
        timeout: Request timeout in seconds
    
    Returns:
        List of results for each URL
    """
    return [check_url(url, timeout) for url in urls]


if __name__ == "__main__":
    # Example usage
    urls = [
        "https://example.com",
        "https://httpbin.org/status/404",
        "https://invalid-url-that-does-not-exist.xyz"
    ]
    
    for result in check_urls(urls):
        status = "✓" if result["accessible"] else "✗"
        print(f"{status} {result['url']}: {result.get('status', 'N/A')}")
