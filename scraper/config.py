"""
Configuración del scraper de Valora Analitik.

Este módulo contiene todas las constantes y configuraciones necesarias
para el funcionamiento del scraper de noticias financieras.
"""
from typing import Dict, List

# Validación de rango temporal
MIN_DAYS = 1
MAX_DAYS = 365
DEFAULT_SINCE_DAYS: int = 30  # Días hacia atrás para buscar noticias

# URLs base
BASE_URL: str = "https://www.valoraanalitik.com"

# URLs de categorías de "Últimas Noticias"
CATEGORIAS_ULTIMAS_NOTICIAS: Dict[str, str] = {
    "infraestructura": f"{BASE_URL}/noticias-de-infraestructura/",
    "macroeconomicas": f"{BASE_URL}/noticias-macroeconomicas/",
    "empresariales": f"{BASE_URL}/noticias-empresariales/",
    "petroleras": f"{BASE_URL}/noticias-petroleras/",
    "mineria_energia": f"{BASE_URL}/noticias-de-mineria-y-energia/",
    "monedas": f"{BASE_URL}/noticias-de-monedas/",
    "criptomonedas": f"{BASE_URL}/noticias-de-criptomonedas/",
    "mercados_financieros": f"{BASE_URL}/noticias-de-mercados-financieros/",
}

# Configuración de búsqueda (mantenidas para compatibilidad)
BASE_SEARCH_URL: str = "https://www.valoraanalitik.com/?s={query}"
MAX_SEARCH_PAGES: int = 5  # Máximo de páginas de resultados por categoría

# Configuración de Scrapy para rate limiting y respeto al servidor
SPIDER_SETTINGS: Dict[str, any] = {
    "DOWNLOAD_DELAY": 0.8,  # Espera entre requests al mismo dominio
    "RANDOMIZE_DOWNLOAD_DELAY": True,
    "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
    "AUTOTHROTTLE_ENABLED": True,
    "AUTOTHROTTLE_START_DELAY": 0.5,
    "AUTOTHROTTLE_MAX_DELAY": 5.0,
    "FEED_EXPORT_ENCODING": "utf-8",
    "DEFAULT_REQUEST_HEADERS": {
        "User-Agent": "Mozilla/5.0 (compatible; ValoraScraper/1.0; +https://example.org)"
    }
}

# Selectores CSS para encontrar elementos en las páginas
ARTICLE_CARD_SELECTORS: str = ".jeg_post, article, .post"
PAGINATION_SELECTORS: List[str] = ["a.next", ".page-numbers a", "a[rel='next']"]


def validar_configuracion() -> bool:
    """
    Valida que la configuración sea correcta.
    
    Returns:
        True si la configuración es válida
        
    Raises:
        ValueError: Si alguna configuración es inválida
    """
    if not BASE_URL.startswith("http"):
        raise ValueError(f"BASE_URL debe ser una URL válida: {BASE_URL}")
    
    if not CATEGORIAS_ULTIMAS_NOTICIAS:
        raise ValueError("CATEGORIAS_ULTIMAS_NOTICIAS no puede estar vacío")
    
    if MAX_SEARCH_PAGES < 1:
        raise ValueError(f"MAX_SEARCH_PAGES debe ser al menos 1: {MAX_SEARCH_PAGES}")
    
    return True
