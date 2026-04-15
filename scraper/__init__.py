"""
Módulo scraper para extraer noticias de Valora Analitik.
"""
from .valora_spider import ValoraSpider
from .utils import detectar_sector, parse_article_date
from .config import DEFAULT_SINCE_DAYS, BASE_SEARCH_URL

__all__ = [
    "ValoraSpider",
    "detectar_sector", 
    "parse_article_date",
    "DEFAULT_SINCE_DAYS",
    "BASE_SEARCH_URL"
]
