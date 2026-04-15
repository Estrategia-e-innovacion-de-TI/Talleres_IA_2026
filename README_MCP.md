# MCP Server - Valora Scraper

Servidor MCP (Model Context Protocol) para ejecutar el scraper de noticias de Valora Analitik.

## Instalación

El proyecto ya tiene las dependencias necesarias en `pyproject.toml`. Asegúrate de instalarlas:

```bash
uv sync
```

## Herramientas disponibles

### 1. `ejecutar_scraper_valora`
Inicia el scraper de Valora Analitik en background (no bloquea).

**Parámetros:**
- `since_days` (int, opcional): Número de días hacia atrás para buscar (default: 30)
- `output_format` (str, opcional): Formato de salida 'json' o 'jsonlines' (default: json)

**Retorna inmediatamente** un ID de trabajo. El scraper continúa ejecutándose en segundo plano.

**Ejemplo:**
```python
# Inicia el scraper (retorna inmediatamente)
ejecutar_scraper_valora(since_days=60)
# Retorna: "Scraper iniciado en background. ID del trabajo: abc123..."
```

### 2. `obtener_estado_scraper`
Consulta el estado de un trabajo de scraping.

**Parámetros:**
- `job_id` (str, opcional): ID del trabajo (muestra todos si no se especifica)

**Ejemplo:**
```python
# Consultar estado de un trabajo específico
obtener_estado_scraper(job_id="abc123")

# Ver todos los trabajos
obtener_estado_scraper()
```

### 3. `leer_noticias_valora`
Lee y filtra las noticias extraídas previamente.

**Parámetros:**
- `archivo` (str, opcional): Ruta del archivo JSON (usa el más reciente si no se especifica)
- `sector` (str, opcional): Filtrar por sector
  - `minero_energetico`
  - `financiero`
  - `construccion`
  - `telecom`
  - `fondos_bursatiles`
- `limite` (int, opcional): Número máximo de noticias a retornar

**Ejemplo:**
```python
leer_noticias_valora(sector="financiero", limite=10)
```

## Uso del servidor MCP

### Opción 1: Ejecutar directamente con uv
```bash
uv run mcp_server.py
```

### Opción 2: Configurar en Claude Desktop

Agrega esto a tu archivo de configuración de Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "valora-scraper": {
      "command": "uv",
      "args": ["run", "mcp_server.py"],
      "cwd": "c:\\Users\\marmenes\\Documents\\agente_inversion"
    }
  }
}
```

O con la ruta completa:

```json
{
  "mcpServers": {
    "valora-scraper": {
      "command": "uv",
      "args": ["run", "c:\\Users\\marmenes\\Documents\\agente_inversion\\mcp_server.py"]
    }
  }
}
```

## Prueba rápida

Puedes probar el servidor ejecutándolo directamente:

```bash
uv run mcp_server.py
```

El servidor se iniciará y estará listo para recibir comandos MCP desde cualquier cliente compatible.

## Estructura de datos

Las noticias extraídas tienen el siguiente formato:

```json
{
  "id": 1,
  "titulo": "Título de la noticia",
  "url": "https://www.valoraanalitik.com/...",
  "fecha": "2026-03-25T10:30:00",
  "sectores": ["financiero", "construccion"],
  "resumen": "Resumen breve...",
  "contenido": "Contenido completo...",
  "origen": "Valora Analitik",
  "extraido_en": "2026-03-25T15:45:00"
}
```

## Notas

- **Ejecución asíncrona**: El scraper se ejecuta en background y responde inmediatamente
- Evita timeouts del cliente MCP al no bloquear durante la ejecución
- Usa `obtener_estado_scraper()` para monitorear el progreso
- El scraper respeta los límites de velocidad del servidor
- Solo guarda noticias de los 5 sectores definidos
- Las noticias se guardan en archivos JSON con formato `noticias_valora_XXdias.json`

## Flujo de trabajo típico

```python
# 1. Iniciar el scraper
job = ejecutar_scraper_valora(since_days=30)
# Retorna inmediatamente con un job_id

# 2. Consultar estado (después de unos minutos)
obtener_estado_scraper(job_id="abc123")

# 3. Cuando esté completado, leer las noticias
leer_noticias_valora(sector="financiero", limite=5)
```
