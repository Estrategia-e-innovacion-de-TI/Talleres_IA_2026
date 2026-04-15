"""
Spider para extraer noticias financieras de Valora Analitik.

Este spider scrape noticias de las categorías configuradas en config.py,
filtra por fecha, y extrae contenido relevante incluyendo título,
fecha, resumen, contenido completo y clasificación por sectores.
"""
import scrapy
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin
from typing import Generator, Set, Optional, Dict, Any, AsyncGenerator
from selectolax.lexbor import LexborHTMLParser

logger = logging.getLogger(__name__)

# Imports absolutos para compatibilidad con scrapy runspider
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    DEFAULT_SINCE_DAYS,
    BASE_URL,
    CATEGORIAS_ULTIMAS_NOTICIAS,
    MAX_SEARCH_PAGES,
    SPIDER_SETTINGS,
    ARTICLE_CARD_SELECTORS,
    PAGINATION_SELECTORS
)
from utils import (
    KEYWORDS,
    detectar_sector,
    parse_article_date,
    extraer_contenido_articulo,
    crear_resumen
)

# Constantes de configuración del spider
MIN_TITLE_LENGTH: int = 10  # Título mínimo válido
MIN_CONTENT_LENGTH: int = 50  # Contenido mínimo válido


class ValoraSpider(scrapy.Spider):
    """
    Spider para extraer noticias financieras de Valora Analitik.
    
    Attributes:
        name: Identificador único del spider
        allowed_domains: Dominios permitidos para scraping
        cutoff_date: Fecha de corte para filtrar noticias antiguas
        seen_urls: Set de URLs ya visitadas para evitar duplicados
        article_counter: Contador de artículos extraídos
    """
    
    name: str = "valora_spider"
    allowed_domains: list[str] = ["valoraanalitik.com"]
    custom_settings: Dict[str, Any] = SPIDER_SETTINGS

    def __init__(self, since_days: Optional[str] = None, *args, **kwargs):
        """
        Inicializa el spider con configuración de fecha.
        
        Args:
            since_days: Número de días hacia atrás para filtrar noticias.
                       Si no se proporciona, usa DEFAULT_SINCE_DAYS de config.
        """
        super().__init__(*args, **kwargs)
        
        # Validar y parsear since_days
        try:
            days = int(since_days) if since_days else DEFAULT_SINCE_DAYS
            if days < 1:
                logger.warning(f"since_days debe ser positivo, usando default: {DEFAULT_SINCE_DAYS}")
                days = DEFAULT_SINCE_DAYS
        except (ValueError, TypeError) as e:
            logger.warning(f"Error al parsear since_days='{since_days}': {e}. Usando default: {DEFAULT_SINCE_DAYS}")
            days = DEFAULT_SINCE_DAYS
        
        self.cutoff_date: datetime = datetime.now() - timedelta(days=days)
        self.seen_urls: Set[str] = set()
        self.article_counter: int = 1
        
        logger.info(f"ValoraSpider iniciado: buscando noticias desde {self.cutoff_date.strftime('%Y-%m-%d')}")

    def start_requests(self):
        """Genera requests iniciales para cada categoría configurada."""
        logger.info(f"Iniciando scraping de {len(CATEGORIAS_ULTIMAS_NOTICIAS)} categorías")
        
        for categoria, url in CATEGORIAS_ULTIMAS_NOTICIAS.items():
            logger.info(f"➡️ Iniciando categoría: {categoria}")
            yield scrapy.Request(
                url, 
                callback=self.parse_categoria, 
                meta={
                    "categoria": categoria,
                    "page": 1
                },
                errback=self.errback_httpbin
            )

    def errback_httpbin(self, failure):
        """Maneja errores en requests HTTP."""
        logger.error(f"Request falló: {failure.request.url}")
        logger.error(f"Razón: {failure.value}")

    def parse_categoria(self, response) -> Generator[scrapy.Request, None, None]:
        """
        Parsea páginas de categorías y extrae enlaces a artículos.
        También maneja paginación para cargar más noticias.
        
        Args:
            response: Respuesta HTTP de Scrapy
            
        Yields:
            Requests para seguir artículos individuales o páginas de paginación
        """
        try:
            tree = LexborHTMLParser(response.text)
        except Exception as e:
            logger.error(f"Error al parsear HTML de {response.url}: {e}")
            return
        
        categoria = response.meta.get("categoria", "desconocida")
        current_page = response.meta.get("page", 1)

        logger.debug(f"Parseando '{categoria}' - Página {current_page}")

        # Extraer enlaces de artículos
        articles_found = 0
        cards = tree.css(ARTICLE_CARD_SELECTORS)
        for card in cards:
            link = card.css_first("a")
            if not link:
                continue
            
            href = link.attributes.get("href")
            if not href:
                continue
            
            url = href if href.startswith("http") else urljoin(response.url, href)
            
            if self._is_valid_url(url):
                self.seen_urls.add(url)
                articles_found += 1
                yield response.follow(
                    url, 
                    callback=self.parse_article,
                    meta={"categoria": categoria}
                )

        self.logger.info(f"Encontrados {articles_found} artículos en categoría '{categoria}' - Página {current_page}")

        # Buscar enlaces de paginación (botones "ver más", "siguiente", etc.)
        if current_page < MAX_SEARCH_PAGES:
            # Intentar con diferentes selectores de paginación
            pagination_selectors = [
                "a.next",
                ".page-numbers a",
                "a[rel='next']",
                ".load-more",
                ".ver-mas",
                ".pagination a",
                "a:contains('Ver más')",
                "a:contains('Cargar más')",
                "a:contains('Siguiente')",
            ]
            
            for selector in pagination_selectors:
                next_links = tree.css(selector)
                for link in next_links:
                    href = link.attributes.get("href")
                    if not href:
                        continue
                    
                    next_url = href if href.startswith("http") else urljoin(response.url, href)
                    
                    if self._is_valid_url(next_url):
                        self.seen_urls.add(next_url)
                        self.logger.info(f"Siguiendo paginación en categoría '{categoria}' -> Página {current_page + 1}")
                        yield response.follow(
                            next_url,
                            callback=self.parse_categoria,
                        meta={
                            "categoria": categoria,
                            "page": current_page + 1
                        },
                        errback=self.errback_httpbin
                    )
                    break  # Solo seguir un enlace de paginación por página

    def parse(self, response) -> Generator[scrapy.Request, None, None]:
        """Método parse heredado de Spider - redirige a parse_categoria."""
        return self.parse_categoria(response)

    def parse_article(self, response):
        """
        Parsea un artículo individual y extrae toda la información relevante.
        
        Args:
            response: Respuesta HTTP de Scrapy
            
        Returns:
            Diccionario con los datos del artículo o None si es inválido
        """
        try:
            tree = LexborHTMLParser(response.text)
        except Exception as e:
            logger.error(f"Error al parsear artículo {response.url}: {e}")
            return None
        
        categoria = response.meta.get("categoria", "desconocida")
        
        # Extraer título y contenido
        try:
            titulo, contenido_completo = extraer_contenido_articulo(tree)
        except Exception as e:
            logger.error(f"Error al extraer contenido de {response.url}: {e}")
            return None
        
        if not titulo or len(titulo) < MIN_TITLE_LENGTH:
            logger.warning(f"Título inválido o muy corto en: {response.url}")
            return None
        
        if not contenido_completo or len(contenido_completo) < MIN_CONTENT_LENGTH:
            logger.warning(f"Contenido inválido o muy corto en: {response.url}")
            return None
        
        # Extraer y validar fecha
        try:
            fecha = parse_article_date(tree)
        except Exception as e:
            logger.error(f"Error al extraer fecha de {response.url}: {e}")
            return None
        
        if not fecha:
            logger.warning(f"No se pudo extraer fecha de: {response.url}")
            return None
        
        if fecha < self.cutoff_date:
            logger.debug(f"Artículo antiguo ({fecha.strftime('%Y-%m-%d')}): {response.url}")
            return None
        
        # Extraer párrafos para el resumen
        try:
            parrafos = [
                p.text().strip() 
                for p in tree.css("article p, .entry-content p, .content p") 
                if p.text().strip()
            ]
            resumen = crear_resumen(parrafos)
        except Exception as e:
            logger.warning(f"Error al crear resumen de {response.url}: {e}")
            resumen = contenido_completo[:400] + "..."
        
        # Clasificar por sectores (detección automática)
        texto_completo = f"{titulo} {contenido_completo}"
        try:
            sectores = detectar_sector(texto_completo)
        except Exception as e:
            logger.warning(f"Error al detectar sectores en {response.url}: {e}")
            sectores = []
        
        # Si no se detectaron sectores automáticamente, usar la categoría
        if not sectores:
            sectores = [categoria]
        
        logger.info(f"✓ Artículo #{self.article_counter}: {titulo[:60]}... | {categoria} | {fecha.strftime('%Y-%m-%d')}")
        
        yield {
            "id": self.article_counter,
            "titulo": titulo,
            "url": response.url,
            "fecha": fecha.strftime("%Y-%m-%dT%H:%M:%S"),
            "categoria": categoria,
            "sectores": sectores,
            "resumen": resumen,
            "contenido": contenido_completo,
            "origen": "Valora Analitik",
            "extraido_en": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        
        self.article_counter += 1

    def _is_valid_url(self, url: str) -> bool:
        """
        Verifica si una URL es válida y no ha sido visitada.
        
        Args:
            url: URL a validar
            
        Returns:
            True si la URL es válida y no visitada, False en caso contrario
        """
        if not url or not isinstance(url, str):
            return False
        
        if url in self.seen_urls:
            return False
        
        # Verificar que sea del dominio permitido
        if not any(domain in url for domain in self.allowed_domains):
            return False
        
        return True





