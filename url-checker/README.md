# URL Checker Tool Module

A simple tool to check if URLs are accessible.

## Usage

```python
from url_checker import check_url

result = check_url("https://example.com")
print(result)
```

## Functions

- `check_url(url, timeout=10)` - Check if a URL is accessible
- `check_urls(urls, timeout=10)` - Check multiple URLs
