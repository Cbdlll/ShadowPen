"""
Utils module: Custom Exceptions

Defines exception classes used by the crawler engine
"""


class CrawlerException(Exception):
    """Base crawler exception"""
    pass


class TimeoutException(CrawlerException):
    """Timeout exception"""
    pass


class BrowserException(CrawlerException):
    """Browser-related exception"""
    pass


class NavigationException(CrawlerException):
    """Page navigation exception"""
    pass


class InteractionException(CrawlerException):
    """Interaction exception"""
    pass
