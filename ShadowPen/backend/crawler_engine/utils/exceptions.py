"""
工具模块：自定义异常

定义爬虫引擎使用的异常类
"""


class CrawlerException(Exception):
    """爬虫基础异常"""
    pass


class TimeoutException(CrawlerException):
    """超时异常"""
    pass


class BrowserException(CrawlerException):
    """浏览器相关异常"""
    pass


class NavigationException(CrawlerException):
    """页面导航异常"""
    pass


class InteractionException(CrawlerException):
    """交互触发异常"""
    pass
