"""
Listado de empresas que cotizan en la Bolsa de Valores de Colombia (BVC).

Este módulo contiene la base de datos de empresas listadas en la BVC
con sus tickers, nombres completos, sectores y keywords para detección
automática en noticias.

Actualizado: Marzo 2026
"""
import re
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Tipo para la estructura de datos de empresas
EmpresaInfo = Dict[str, any]

EMPRESAS_BVC: Dict[str, EmpresaInfo] = {
    # Energía y Petróleo
    "ECOPETROL": {
        "ticker": "ECOPETROL",
        "nombre_completo": "Ecopetrol S.A.",
        "sector": "Petróleo y Gas",
        "keywords": ["ecopetrol", "hocol", "refinería barrancabermeja", "ricardo roa"]
    },
    "CELSIA": {
        "ticker": "CELSIA",
        "nombre_completo": "Celsia S.A. E.S.P.",
        "sector": "Energía",
        "keywords": ["celsia", "grupo argos energía"]
    },
    "ISA": {
        "ticker": "ISA",
        "nombre_completo": "Interconexión Eléctrica S.A. E.S.P.",
        "sector": "Energía - Transmisión",
        "keywords": ["isa", "interconexión eléctrica", "transmisión energía", "transmisión eléctrica"]
    },
    "GEB": {
        "ticker": "EEB",
        "nombre_completo": "Grupo Energía Bogotá S.A. E.S.P.",
        "sector": "Energía",
        "keywords": ["geb", "grupo energía bogotá", "eeb", "empresa energía bogotá"]
    },
    "PROMIGAS": {
        "ticker": "PROMIGAS",
        "nombre_completo": "Promigas S.A. E.S.P.",
        "sector": "Gas Natural",
        "keywords": ["promigas", "gas natural"]
    },
    
    # Financiero
    "BANCOLOMBIA": {
        "ticker": "CIBEST",
        "nombre_completo": "Bancolombia S.A.",
        "sector": "Financiero",
        "keywords": ["bancolombia", "banco colombia"]
    },
    "BANCOLOMBIA_PREF": {
        "ticker": "PFCIBEST",
        "nombre_completo": "Bancolombia S.A. Preferencial",
        "sector": "Financiero",
        "keywords": ["bancolombia preferencial", "pf bancolombia", "banco colombia preferencial"]
    },
    "DAVIVIENDA": {
        "ticker": "PFDAVVNDA",
        "nombre_completo": "Banco Davivienda S.A.",
        "sector": "Financiero",
        "keywords": ["davivienda", "banco davivienda"]
    },
    "BOGOTA": {
        "ticker": "BOGOTA",
        "nombre_completo": "Banco de Bogotá S.A.",
        "sector": "Financiero",
        "keywords": ["banco de bogotá", "banco bogotá"]
    },
    "GRUPOAVAL": {
        "ticker": "PFAVAL",
        "nombre_completo": "Grupo Aval Acciones y Valores S.A.",
        "sector": "Holding Financiero",
        "keywords": ["grupo aval", "pf aval"]
    },
    "CORFICOLOMBIANA": {
        "ticker": "CORFICOLCF",
        "nombre_completo": "Corporación Financiera Colombiana S.A.",
        "sector": "Financiero",
        "keywords": ["corficolombiana", "corficolcf"]
    },
    "GRUPOSURA": {
        "ticker": "GRUPOSURA",
        "nombre_completo": "Grupo de Inversiones Suramericana S.A.",
        "sector": "Holding Financiero",
        "keywords": ["grupo sura", "pf grupo sura", "suramericana"]
    },
    "GRUPOBOLIVAR": {
        "ticker": "GRUPOBOLIVAR",
        "nombre_completo": "Grupo Bolívar S.A.",
        "sector": "Seguros",
        "keywords": ["grupo bolívar", "grupo bolivar"]
    },
    "BVC": {
        "ticker": "BVC",
        "nombre_completo": "Bolsa de Valores de Colombia S.A.",
        "sector": "Mercado de Capitales",
        "keywords": ["bvc", "bolsa de valores colombia", "bolsa colombia"]
    },
    
    # Construcción y Materiales
    "GRUPOARGOS": {
        "ticker": "GRUPOARGOS",
        "nombre_completo": "Grupo Argos S.A.",
        "sector": "Holding",
        "keywords": ["grupo argos"]
    },
    "CEMARGOS": {
        "ticker": "CEMARGOS",
        "nombre_completo": "Cementos Argos S.A.",
        "sector": "Materiales de Construcción",
        "keywords": ["cementos argos", "pf cementos argos"]
    },
    "CONCONCRETO": {
        "ticker": "CONCONCRET",
        "nombre_completo": "Constructora Conconcreto S.A.",
        "sector": "Construcción",
        "keywords": ["conconcreto", "constructora conconcreto"]
    },
    
    # Comercio y Retail
    "EXITO": {
        "ticker": "ÉXITO",
        "nombre_completo": "Almacenes Éxito S.A.",
        "sector": "Retail",
        "keywords": ["éxito", "almacenes éxito", "carulla", "surtimax"]
    },
    "NUTRESA": {
        "ticker": "NUTRESA",
        "nombre_completo": "Grupo Nutresa S.A.",
        "sector": "Alimentos",
        "keywords": ["nutresa", "grupo nutresa"]
    },
    
    # Telecomunicaciones
    "ETB": {
        "ticker": "ETB",
        "nombre_completo": "Empresa de Telecomunicaciones de Bogotá S.A. E.S.P.",
        "sector": "Telecomunicaciones",
        "keywords": ["etb", "empresa telecomunicaciones bogotá"]
    },
    
    # Minería
    "MINEROS": {
        "ticker": "MINEROS",
        "nombre_completo": "Mineros S.A.",
        "sector": "Minería - Oro",
        "keywords": ["mineros", "mineros s.a.", "minería oro"]
    },
    
    # Combustibles
    "TERPEL": {
        "ticker": "TERPEL",
        "nombre_completo": "Organización Terpel S.A.",
        "sector": "Combustibles",
        "keywords": ["terpel", "acciones de terpel", "acción de terpel"]
    },
    
    # Otros
    "ENKA": {
        "ticker": "ENKA",
        "nombre_completo": "Enka de Colombia S.A.",
        "sector": "Textil",
        "keywords": ["enka"]
    },
    "CNEC": {
        "ticker": "CNEC",
        "nombre_completo": "Canacol Energy Colombia S.A.S.",
        "sector": "Petróleo y Gas",
        "keywords": ["canacol", "canacol energy"]
    },
    "COLCAP": {
        "ticker": "COLCAP",
        "nombre_completo": "Índice MSCI Colcap",
        "sector": "Índice",
        "keywords": ["colcap", "msci colcap", "índice colcap"]
    }
}


def buscar_empresas_en_texto(texto: str, case_sensitive: bool = False) -> List[str]:
    """
    Busca menciones de empresas de la BVC en un texto.
    
    Args:
        texto: Texto donde buscar las empresas
        case_sensitive: Si True, búsqueda sensible a mayúsculas/minúsculas
    
    Returns:
        Lista de tickers de empresas encontradas (sin duplicados)
        
    Raises:
        ValueError: Si el texto es None o vacío
        
    Examples:
        >>> buscar_empresas_en_texto("Ecopetrol anunció ganancias y Bancolombia sube")
        ['ECOPETROL', 'BANCOLOMBIA']
    """
    if not texto or not isinstance(texto, str):
        logger.warning("buscar_empresas_en_texto recibió texto inválido")
        raise ValueError("El texto debe ser una cadena no vacía")
    
    texto_busqueda = texto if case_sensitive else texto.lower()
    empresas_encontradas: Set[str] = set()  # Usar set para evitar duplicados
    
    for ticker, info in EMPRESAS_BVC.items():
        # Buscar por keywords con word boundaries para mayor precisión
        for keyword in info["keywords"]:
            keyword_busqueda = keyword if case_sensitive else keyword.lower()
            
            # Usar word boundaries para evitar coincidencias parciales
            pattern = rf"\b{re.escape(keyword_busqueda)}\b"
            if re.search(pattern, texto_busqueda):
                empresas_encontradas.add(ticker)
                logger.debug(f"Empresa {ticker} detectada por keyword '{keyword}'")
                break  # Ya encontramos esta empresa, no seguir buscando keywords
    
    result = list(empresas_encontradas)
    logger.info(f"Encontradas {len(result)} empresas en el texto")
    return result


def obtener_info_empresa(ticker: str) -> Optional[EmpresaInfo]:
    """
    Obtiene la información completa de una empresa por su ticker.
    
    Args:
        ticker: Ticker de la empresa en la BVC (e.g., 'ECOPETROL', 'BANCOLOMBIA')
    
    Returns:
        Diccionario con la información de la empresa (ticker, nombre_completo, 
        sector, keywords) o None si el ticker no existe
        
    Raises:
        ValueError: Si ticker es None o vacío
        
    Examples:
        >>> info = obtener_info_empresa('ECOPETROL')
        >>> info['nombre_completo']
        'Ecopetrol S.A.'
    """
    if not ticker or not isinstance(ticker, str):
        logger.warning(f"obtener_info_empresa recibió ticker inválido: {ticker}")
        raise ValueError("El ticker debe ser una cadena no vacía")
    
    # Normalizar ticker a uppercase para búsqueda
    ticker_upper = ticker.upper()
    info = EMPRESAS_BVC.get(ticker_upper)
    
    if info is None:
        logger.debug(f"Ticker '{ticker}' no encontrado en EMPRESAS_BVC")
    
    return info


def obtener_todas_empresas() -> List[str]:
    """
    Obtiene la lista de todos los tickers disponibles.
    
    Returns:
        Lista de tickers de todas las empresas en la BVC
    """
    return list(EMPRESAS_BVC.keys())


def obtener_empresas_por_sector(sector: str) -> List[str]:
    """
    Obtiene la lista de tickers de empresas de un sector específico.
    
    Args:
        sector: Nombre del sector (e.g., 'Financiero', 'Energía')
    
    Returns:
        Lista de tickers del sector especificado
        
    Examples:
        >>> obtener_empresas_por_sector('Financiero')
        ['BANCOLOMBIA', 'DAVIVIENDA', 'BOGOTA', ...]
    """
    if not sector:
        logger.warning("obtener_empresas_por_sector recibió sector vacío")
        return []
    
    sector_lower = sector.lower()
    return [
        ticker 
        for ticker, info in EMPRESAS_BVC.items() 
        if info["sector"].lower() == sector_lower
    ]
