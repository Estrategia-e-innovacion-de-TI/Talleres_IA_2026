"""
Utilidades para el scraper de Valora Analitik.

Este módulo contiene funciones de utilidad para procesar HTML,
extraer fechas, limpiar texto y clasificar noticias por sector.
"""
from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from selectolax.lexbor import LexborHTMLParser

logger = logging.getLogger(__name__)

# Palabras clave para clasificar por sector
KEYWORDS: Dict[str, List[str]] = {
    "minero_energetico": [
        "ecopetrol", "minería", "minero", "petróleo", "gas", "carbón", "hidroeléctrica",
        "creg", "transición energética", "eléctrica", "geopark", "frontera energy", "parex",
        "isa", "grupo energía bogotá"
    ],
    "financiero": [
        "banco", "bancario", "financiero", "superfinanciera", "bvc", "tes",
        "tarjetas", "crédito", "inclusión financiera", "davivienda", "bancolombia", "bbva", "grupo aval"
    ],
    "construccion": [
        "construcción", "vivienda", "vis", "vip", "camacol", "inmobiliario", "infraestructura",
        "concesión", "metro", "aeropuerto", "obra", "licencia"
    ],
    "telecom": [
        "telecom", "5g", "4g", "fibra", "espectro", "torres", "claro", "tigo", "movistar", "une", "wom",
        "antena", "conectividad"
    ],
    "fondos_bursatiles": [
        "etf", "fondo bursátil", "mercado global colombiano", "ishares", "blackrock", "vaneck",
        "first trust", "spdr", "semiconductores", "oro"
    ],
}


def detectar_sector(text: str) -> List[str]:
    """
    Detecta los sectores de una noticia basándose en palabras clave.
    
    Args:
        text: Texto a analizar (típicamente título + contenido)
    
    Returns:
        Lista de sectores detectados (vacía si no se encuentra ninguno)
        
    Raises:
        ValueError: Si text es None o vacío
    """
    if not text or not isinstance(text, str):
        logger.warning("detectar_sector recibió texto inválido")
        raise ValueError("El texto debe ser una cadena no vacía")
    
    text_lower = text.lower()
    sectores = []
    
    for sector, keywords in KEYWORDS.items():
        for keyword in keywords:
            # Usar word boundaries para evitar coincidencias parciales
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                sectores.append(sector)
                break
    
    logger.debug(f"Detectados {len(sectores)} sectores en el texto")
    return sectores


def parse_article_date(tree: LexborHTMLParser) -> Optional[datetime]:
    """
    Extrae y parsea la fecha de un artículo desde el HTML.
    
    Intenta múltiples estrategias:
    1. Atributo datetime del elemento <time>
    2. Texto del elemento <time>
    3. Meta tags de Open Graph/Article
    4. Búsqueda de patrón de fecha en la página
    
    Args:
        tree: Árbol HTML parseado con LexborHTMLParser
    
    Returns:
        Objeto datetime (naive, UTC) o None si no se pudo extraer
        
    Raises:
        ValueError: Si tree no es un LexborHTMLParser válido
    """
    if not isinstance(tree, LexborHTMLParser):
        logger.error("parse_article_date requiere un LexborHTMLParser")
        raise ValueError("tree debe ser una instancia de LexborHTMLParser")
    
    # Estrategia 1: Buscar elemento <time> con atributo datetime
    time_node = tree.css_first("time")
    if time_node:
        dt_attr = time_node.attributes.get("datetime")
        if dt_attr:
            dt = _parse_iso_datetime(dt_attr)
            if dt:
                return dt
        
        # Intentar extraer fecha del texto del elemento <time>
        text = time_node.text().strip()
        match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d")
            except ValueError:
                pass
    
    # Estrategia 2: Buscar meta tags de Open Graph/Article
    for meta in tree.css("meta"):
        prop = meta.attributes.get("property", "").lower()
        if prop in {"article:published_time", "og:updated_time"}:
            content = meta.attributes.get("content", "")
            if content:
                dt = _parse_iso_datetime(content)
                if dt:
                    return dt
    
    # Estrategia 3: Fallback - buscar patrón de fecha en toda la página
    match = re.search(r"(\d{4}-\d{2}-\d{2})", tree.html or "")
    if match:
        try:
            logger.debug(f"Fecha encontrada con fallback: {match.group(1)}")
            return datetime.strptime(match.group(1), "%Y-%m-%d")
        except ValueError as e:
            logger.warning(f"Error al parsear fecha {match.group(1)}: {e}")
    
    logger.warning("No se pudo extraer la fecha del artículo")
    return None


def _parse_iso_datetime(date_string: str) -> Optional[datetime]:
    """
    Parsea una fecha en formato ISO y retorna datetime naive.
    
    Args:
        date_string: Fecha en formato ISO (puede incluir timezone)
    
    Returns:
        Datetime naive o None si falla el parseo
    """
    if not date_string:
        return None
        
    try:
        # Reemplazar 'Z' por '+00:00' para compatibilidad
        normalized = date_string.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        
        # Convertir a naive si tiene timezone
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        
        return dt
    except (ValueError, AttributeError) as e:
        logger.debug(f"Error al parsear fecha ISO '{date_string}': {e}")
        return None


def extraer_contenido_articulo(tree: LexborHTMLParser) -> Tuple[str, str]:
    """
    Extrae el título y contenido de un artículo.
    
    Args:
        tree: Árbol HTML parseado
    
    Returns:
        Tupla (título, contenido) - ambos como strings limpios
        
    Raises:
        ValueError: Si tree no es un LexborHTMLParser válido
    """
    if not isinstance(tree, LexborHTMLParser):
        logger.error("extraer_contenido_articulo requiere un LexborHTMLParser")
        raise ValueError("tree debe ser una instancia de LexborHTMLParser")
    
    # Extraer título
    title_node = tree.css_first("h1") or tree.css_first(".entry-title")
    titulo = title_node.text().strip() if title_node else ""
    titulo = _limpiar_texto(titulo)
    
    # Extraer párrafos del artículo
    parrafos = [
        _limpiar_texto(p.text().strip())
        for p in tree.css("article p, .entry-content p, .content p") 
        if p.text().strip()
    ]
    contenido = "\n".join(parrafos)
    
    logger.debug(f"Extraído: título={len(titulo)} chars, contenido={len(contenido)} chars")
    return titulo, contenido


def _limpiar_texto(texto: str) -> str:
    """
    Limpia el texto para evitar problemas al serializar a JSON.
    
    Args:
        texto: Texto a limpiar
    
    Returns:
        Texto limpio
    """
    if not texto:
        return ""
    
    # Normalizar espacios en blanco
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar caracteres de control excepto saltos de línea y tabs
    texto = ''.join(char for char in texto if ord(char) >= 32 or char in '\n\t')
    
    # Normalizar comillas para evitar problemas de escape
    texto = texto.replace('\u201c', '"').replace('\u201d', '"')  # Comillas tipográficas
    texto = texto.replace('\u2018', "'").replace('\u2019', "'")  # Apóstrofos tipográficos
    texto = texto.replace('\u2013', '-').replace('\u2014', '-')  # Guiones
    
    return texto.strip()


def crear_resumen(parrafos: List[str], max_length: int = 400) -> str:
    """
    Crea un resumen a partir de los primeros párrafos.
    
    Args:
        parrafos: Lista de párrafos del texto
        max_length: Longitud máxima del resumen (default: 400)
    
    Returns:
        Resumen truncado y limpio
        
    Raises:
        ValueError: Si max_length es menor a 1
    """
    if max_length < 1:
        raise ValueError(f"max_length debe ser al menos 1, recibido: {max_length}")
    
    if not parrafos:
        logger.debug("crear_resumen: lista de párrafos vacía")
        return ""
    
    resumen = " ".join(parrafos[:2])
    resumen = _limpiar_texto(resumen)
    
    if len(resumen) > max_length:
        resumen = resumen[:max_length].rsplit(' ', 1)[0] + "..."
    
    return resumen
