# Changelog - Refactorización Asíncrona

## v2 - Corrección crítica de bloqueo de buffer (2026-03-25)

### 🐛 Bug crítico corregido

**Problema**: El scraper se quedaba bloqueado indefinidamente en Windows debido a `asyncio.subprocess.PIPE`.

**Causa raíz**: 
- Scrapy genera muchos logs (~KB)
- Los PIPEs tienen buffer de 64KB
- Al usar `PIPE` sin leer activamente con `await process.stdout.read()`, el buffer se llenaba
- Una vez lleno, el proceso se pausaba esperando que alguien vaciara el buffer
- Como la función era background sin lectura activa, el scraper nunca terminaba

**Solución aplicada**:
1. ✅ Cambiado de `PIPE` a `DEVNULL` para stdout/stderr
2. ✅ Agregado archivo de log con `--logfile` (Scrapy escribe directamente)
3. ✅ Incluido bloque `finally` para garantizar actualización de estado
4. ✅ Mejorada función `obtener_estado_scraper` para mostrar progreso del log

**Archivos modificados**:
- [server/mcp_server.py](server/mcp_server.py) - Función `_ejecutar_scraper_background`

### 📊 Mejoras adicionales

- Archivo de log individual por trabajo: `scraper_{job_id}.log`
- Muestra progreso en tiempo real al consultar estado
- Logs de error más informativos (últimas 20 líneas del log)
- Tiempo estimado en mensaje de inicio

---

## v1 - Cambios realizados (2026-03-25)

### ✅ Servidor MCP Asíncrono ([server/mcp_server.py](../server/mcp_server.py))

**Problema**: El scraper tardaba mucho y VS Code cerraba la conexión MCP por timeout.

**Solución**: Ejecución asíncrona con sistema de trabajos:

1. **`ejecutar_scraper_valora`** ahora:
   - Retorna inmediatamente con un `job_id`
   - Lanza el scraper en background con `asyncio.create_task()`
   - No bloquea la comunicación MCP

2. **Nueva herramienta**: `obtener_estado_scraper`
   - Consulta el estado de los trabajos (iniciando/ejecutando/completado/error)
   - Muestra progreso, artículos extraídos, errores, etc.
   - Puede listar todos los trabajos activos

3. **`leer_noticias_valora`**: Sin cambios, funciona igual

### ✅ Código refactorizado ([scraper/](../scraper/))

**Antes**: Un archivo monolítico de ~250 líneas

**Ahora**: Estructura modular:
- [scraper/config.py](../scraper/config.py) - Configuración centralizada
- [scraper/utils.py](../scraper/utils.py) - 5 funciones reutilizables
- [scraper/valora_spider.py](../scraper/valora_spider.py) - Spider limpio (~120 líneas)

**Ventajas**:
- Código más legible y mantenible
- Funciones testables individualmente
- Type hints modernos
- Método `async def start()` (Scrapy 2.13+)

## Flujo de trabajo

```bash
# 1. Usuario pide: "Ejecuta el scraper de Valora para 30 días"
ejecutar_scraper_valora(since_days=30)
# → Retorna inmediatamente con job_id: "a1b2c3d4"

# 2. Después de 1-2 minutos: "¿Terminó el scraper?"
obtener_estado_scraper(job_id="a1b2c3d4")
# → Muestra estado: "completado - 45 artículos"

# 3. Lee las noticias: "Dame noticias del sector financiero"
leer_noticias_valora(sector="financiero", limite=10)
# → Retorna JSON con noticias filtradas
```

## Ventajas técnicas

✅ **Sin timeouts**: VS Code no cierra la conexión MCP  
✅ **No bloqueante**: Puedes hacer otras consultas mientras el scraper corre  
✅ **Seguimiento**: Monitorea el progreso en tiempo real  
✅ **Robusto**: Manejo de errores y estados claros  
✅ **Escalable**: Sistema de trabajos permite múltiples scrapers simultáneos  

## Archivos creados/modificados

- ✏️ [server/mcp_server.py](../server/mcp_server.py) - Servidor asíncrono
- ✨ [scraper/config.py](../scraper/config.py) - Nueva
- ✨ [scraper/utils.py](../scraper/utils.py) - Nueva
- ✏️ [scraper/valora_spider.py](../scraper/valora_spider.py) - Refactorizado
- ✨ [scraper/__init__.py](../scraper/__init__.py) - Nueva
- 📖 [scraper/README.md](../scraper/README.md) - Nueva
- 📖 [README_MCP.md](../README_MCP.md) - Actualizado
