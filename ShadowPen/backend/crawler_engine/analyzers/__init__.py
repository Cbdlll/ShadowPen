"""
XSS Crawler Analyzer Module

Contains all attack surface analyzers
"""
from .dom_analyzer import DOMAnalyzer
from .traffic_interceptor import TrafficInterceptor
from .interaction_engine import InteractionEngine
from .deep_interaction_engine import DeepInteractionEngine
from .url_analyzer import URLAnalyzer
from .js_hook_injector import JSHookInjector
from .response_analyzer import ResponseAnalyzer

__all__ = [
    'DOMAnalyzer',
    'TrafficInterceptor',
    'InteractionEngine',
    'DeepInteractionEngine',
    'URLAnalyzer',
    'JSHookInjector',
    'ResponseAnalyzer',
]
