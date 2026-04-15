# Estructura del Scraper Refactorizado

El código del scraper ha sido reorganizado en módulos para mejor mantenibilidad:

## Estructura de archivos

```
scraper/
├── __init__.py          # Punto de entrada del módulo
├── config.py            # Configuración y constantes
├── utils.py             # Funciones de utilidad
└── valora_spider.py     # Spider principal
```

## Módulos

### `config.py`
Contiene toda la configuración del scraper:
- `DEFAULT_SINCE_DAYS`: Días hacia atrás por defecto (30)
- `BASE_SEARCH_URL`: URL base para búsquedas
- `MAX_SEARCH_PAGES`: Límite de páginas a seguir (5)
- `SPIDER_SETTINGS`: Configuración de Scrapy (delays, throttling, etc.)
- `ARTICLE_CARD_SELECTORS`: Selectores CSS para tarjetas de artículos
- `PAGINATION_SELECTORS`: Selectores CSS para paginación

### `utils.py`
Funciones de utilidad reutilizables:

#### `detectar_sector(text: str) -> list[str]`
Detecta sectores de una noticia basándose en palabras clave.

#### `parse_article_date(tree: LexborHTMLParser) -> datetime | None`
Extrae la fecha de un artículo usando múltiples estrategias:
1. Atributo `datetime` del elemento `<time>`
2. Texto del elemento `<time>`
3. Meta tags (Open Graph, Article)
4. Búsqueda de patrón en toda la página

#### `extraer_contenido_articulo(tree: LexborHTMLParser) -> tuple[str, str]`
Extrae título y contenido de un artículo.

#### `crear_resumen(parrafos: list[str], max_length: int = 400) -> str`
Crea un resumen a partir de los primeros párrafos.

#### `KEYWORDS`
Diccionario con palabras clave por sector:
- `minero_energetico`
- `financiero`
- `construccion`
- `telecom`
- `fondos_bursatiles`

### `valora_spider.py`
Spider principal refactorizado con:
- Imports organizados (absolutos para compatibilidad con `scrapy runspider`)
- Método `start()` async (nuevo en Scrapy 2.13+)
- Métodos privados para validación y paginación
- Lógica de negocio separada de utilidades
- Nombres de variables más descriptivos

## Mejoras implementadas

✅ **Separación de responsabilidades**: Lógica, configuración y utilidades en módulos separados  
✅ **Mejor legibilidad**: Nombres descriptivos y métodos más pequeños  
✅ **Reutilización**: Funciones de utils pueden usarse en otros scrapers  
✅ **Mantenibilidad**: Fácil modificar configuración sin tocar el código  
✅ **Type hints**: Uso de anotaciones de tipo modernas con `from __future__ import annotations`  
✅ **Async/await**: Uso de `async def start()` en lugar del deprecado `start_requests()`  

## Uso

```bash
# Ejecutar con configuración por defecto (30 días)
uv run scrapy runspider scraper/valora_spider.py -O noticias.json

# Especificar días hacia atrás
uv run scrapy runspider scraper/valora_spider.py -a since_days=60 -O noticias.json

# Con formato JSONL
uv run scrapy runspider scraper/valora_spider.py -O noticias.jsonl
```

## Via MCP Server

El servidor MCP en [server/mcp_server.py](../server/mcp_server.py) ejecuta automáticamente el scraper:

```python
# Desde Claude/otros clientes MCP
ejecutar_scraper_valora(since_days=30)
leer_noticias_valora(sector="financiero", limite=10)
```
