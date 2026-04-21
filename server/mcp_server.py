"""
- Servidor MCP para ejecutar el scraper de Valora Analitik.
- Consultar en Yahoo finance indicadores financieros

Este servidor proporciona herramientas MCP para:
- Ejecutar scraping de noticias financieras
- Gestionar trabajos en background
- Analizar sentimiento de empresas de la BVC
- Consultar indicadores financieros
"""
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from fastmcp import FastMCP
import os

import yfinance as yf
from curl_cffi import requests
import re

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes de configuración
MAX_SINCE_DAYS = 365  # Máximo de días permitidos
MIN_SINCE_DAYS = 1    # Mínimo de días permitidos
MAX_LOG_LINES = 100   # Máximo de líneas de log a mostrar

# Inicializar el servidor MCP
mcp = FastMCP("Valora Scraper")

# Estado de los trabajos en ejecución (thread-safe dict)
jobs: Dict[str, dict] = {}
# Procesos en ejecución (para poder detenerlos)
processes: Dict[str, asyncio.subprocess.Process] = {}

# Diccionario de mapeo de tickers locales a Yahoo Finance
TICKER_MAP = {
    "BANCOLOMBIA": "CIBEST.CL",
    "BANCOLOMBIA_PREF": "PFCIBEST.CL",
    # Puedes agregar más mapeos aquí si es necesario
}

@mcp.tool()
async def ejecutar_scraper_valora(
    since_days: int = 30,
    output_format: str = "json"
) -> str:
    """
    Inicia el scraper de Valora Analitik para obtener noticias financieras.
    El scraper se ejecuta en background y retorna inmediatamente un ID de trabajo.
    
    Args:
        since_days: Número de días hacia atrás para buscar noticias (default: 30)
        output_format: Formato de salida: 'json' o 'jsonlines' (default: json)
    
    Returns:
        Mensaje con el ID del trabajo y cómo consultar su estado.
        
    Raises:
        ValueError: Si los parámetros están fuera de rango
    """
    # Validar inputs
    if not isinstance(since_days, int):
        return f"❌ Error: 'since_days' debe ser un número entero, recibido: {type(since_days).__name__}"
    
    if since_days < MIN_SINCE_DAYS or since_days > MAX_SINCE_DAYS:
        return f"❌ Error: 'since_days' debe estar entre {MIN_SINCE_DAYS} y {MAX_SINCE_DAYS} días"
    
    if output_format not in ["json", "jsonlines"]:
        return f"❌ Error: 'output_format' debe ser 'json' o 'jsonlines', recibido: {output_format}"
    
    # Generar ID único para este trabajo
    job_id = str(uuid.uuid4())[:8]
    logger.info(f"Iniciando scraper con job_id={job_id}, since_days={since_days}")
    
    # Directorio del proyecto
    project_dir = Path(__file__).parent.parent
    output_file = project_dir / f"noticias_valora_{since_days}dias.json"
    log_file = project_dir / f"scraper_{job_id}.log"
    
    # Registrar el trabajo
    jobs[job_id] = {
        "id": job_id,
        "estado": "iniciando",
        "since_days": since_days,
        "output_file": str(output_file),
        "log_file": str(log_file),
        "iniciado_en": datetime.now().isoformat(),
        "finalizado_en": None,
        "articulos": 0,
        "error": None
    }
    
    # Lanzar el scraper en background
    asyncio.create_task(_ejecutar_scraper_background(job_id, since_days, output_file))
    
    return f"""Scraper iniciado en background.

ID del trabajo: {job_id}
Días a buscar: {since_days}
Archivo de salida: {output_file.name}
Archivo de log: scraper_{job_id}.log

El scraper está ejecutándose. Para consultar el estado usa:
  obtener_estado_scraper(job_id="{job_id}")

Sectores que se extraerán:
- minero_energetico
- financiero
- construccion
- telecom
- fondos_bursatiles

⏱️ Tiempo estimado: 3-10 minutos (dependiendo de la cantidad de noticias)
"""


async def _ejecutar_scraper_background(job_id: str, since_days: int, output_file: Path):
    """Ejecuta el scraper en background y actualiza el estado."""
    try:
        jobs[job_id]["estado"] = "ejecutando"
        
        project_dir = output_file.parent
        
        # Archivo de log para el scraper
        log_file = project_dir / f"scraper_{job_id}.log"
        
        # Construir el comando
        cmd = [
            "uv", "run", "scrapy", "runspider",
            str(project_dir / "scraper" / "valora_spider.py"),
            "-a", f"since_days={since_days}",
            "-O", str(output_file),
            "--logfile", str(log_file)
        ]
        
        # Ejecutar de forma asíncrona sin PIPEs (evita bloqueos de buffer)
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,  # No bloquea el buffer
            stderr=asyncio.subprocess.DEVNULL,  # No bloquea el buffer
            cwd=str(project_dir)
        )
        
        # Guardar el proceso para poder detenerlo si es necesario
        processes[job_id] = process
        
        # Esperar a que termine
        returncode = await process.wait()
        
        # Remover del diccionario de procesos
        if job_id in processes:
            del processes[job_id]
        
        if returncode != 0:
            # Leer el log si hay error
            error_msg = f"El scraper terminó con código {returncode}"
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                        last_lines = f.readlines()[-20:]  # Últimas 20 líneas
                        error_msg += f"\n\nÚltimas líneas del log:\n{''.join(last_lines)}"
                except Exception:
                    pass
            
            jobs[job_id]["estado"] = "error"
            jobs[job_id]["error"] = error_msg
            return
        
        # Verificar y contar artículos
        if output_file.exists():
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    num_articles = len(data) if isinstance(data, list) else 1
                    jobs[job_id]["articulos"] = num_articles
            except Exception:
                jobs[job_id]["articulos"] = 0
        
        jobs[job_id]["estado"] = "completado"
        
    except Exception as e:
        jobs[job_id]["estado"] = "error"
        jobs[job_id]["error"] = str(e)
        
    finally:
        # Asegurar que siempre se actualice la fecha de finalización
        jobs[job_id]["finalizado_en"] = datetime.now().isoformat()


@mcp.tool()
async def obtener_estado_scraper(job_id: str = None, lineas_log: int = 5) -> str:
    """
    Obtiene el estado de un trabajo de scraping con ventana de observación del log.
    
    Args:
        job_id: ID del trabajo (opcional, muestra todos si no se especifica)
        lineas_log: Número de líneas del log a mostrar (default: 5)
    
    Returns:
        Estado del trabajo con las últimas líneas del log.
    """
    if job_id:
        if job_id not in jobs:
            return f"❌ No se encontró el trabajo con ID: {job_id}"
        
        job = jobs[job_id]
        
        # Iconos según estado
        icono_estado = {
            'iniciando': '🔄',
            'ejecutando': '⚙️',
            'completado': '✅',
            'cancelado': '🛑',
            'error': '❌'
        }
        
        icono = icono_estado.get(job['estado'], '❓')
        
        estado_msg = f"""{'='*60}
{'ESTADO DEL SCRAPER':^60}
{'='*60}

{icono} Estado: {job['estado'].upper()}
📋 Job ID: {job_id}
📅 Días solicitados: {job['since_days']}
🕐 Iniciado: {job['iniciado_en']}
🕑 Finalizado: {job['finalizado_en'] or '⏳ En ejecución...'}
📊 Artículos encontrados: {job['articulos']}
📁 Archivo: {Path(job['output_file']).name}
📄 Log: {Path(job['log_file']).name}
"""
        
        # Mostrar últimas líneas del log (ventana de observación)
        log_path = Path(job['log_file'])
        if log_path.exists():
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    all_lines = f.readlines()
                    
                    # Filtrar líneas relevantes (omitir líneas de debug muy técnicas)
                    relevant_lines = []
                    for line in all_lines:
                        line_stripped = line.strip()
                        # Incluir información importante
                        if any(keyword in line_stripped for keyword in [
                            'Crawled', 'Scraped', 'INFO:', 'Spider opened',
                            'Spider closed', 'scraped', 'pages', 'items'
                        ]):
                            relevant_lines.append(line_stripped)
                    
                    # Tomar las últimas N líneas relevantes
                    ultimas_lineas = relevant_lines[-lineas_log:] if relevant_lines else all_lines[-lineas_log:]
                    
                    if ultimas_lineas:
                        estado_msg += f"\n{'─'*60}\n"
                        estado_msg += f"📺 VENTANA DE OBSERVACIÓN (últimas {len(ultimas_lineas)} líneas)\n"
                        estado_msg += f"{'─'*60}\n"
                        for i, line in enumerate(ultimas_lineas, 1):
                            estado_msg += f"{i}. {line}\n"
                        estado_msg += f"{'─'*60}\n"
            except Exception as e:
                estado_msg += f"\n⚠️  No se pudo leer el log: {str(e)}\n"
        else:
            estado_msg += f"\n⚠️  Archivo de log aún no creado\n"
        
        # Información adicional según el estado
        if job['error']:
            estado_msg += f"\n{'─'*60}\n"
            estado_msg += f"❌ ERROR DETECTADO:\n{job['error']}\n"
            estado_msg += f"{'─'*60}\n"
        
        if job['estado'] == 'completado':
            estado_msg += f"\n{'='*60}\n"
            estado_msg += f"{'✅ SCRAPING COMPLETADO EXITOSAMENTE':^60}\n"
            estado_msg += f"{'='*60}\n"
            
            if job['articulos'] > 0:
                estado_msg += f"\n🎉 Se extrajeron {job['articulos']} noticias\n"
                estado_msg += f"\n💡 Para leer las noticias:\n"
                estado_msg += f"   leer_noticias_valora(archivo=\"{job['output_file']}\")\n"
                estado_msg += f"\n💡 Para filtrar por sector:\n"
                estado_msg += f"   leer_noticias_valora(sector=\"financiero\", limite=10)\n"
            else:
                estado_msg += f"\n⚠️  No se encontraron noticias en el período especificado\n"
                estado_msg += f"💡 Intenta aumentar el número de días\n"
        
        elif job['estado'] == 'ejecutando':
            estado_msg += f"\n{'─'*60}\n"
            estado_msg += f"⏳ El scraper está trabajando...\n"
            estado_msg += f"💡 Consulta de nuevo en 30-60 segundos:\n"
            estado_msg += f"   obtener_estado_scraper(job_id=\"{job_id}\")\n"
            estado_msg += f"{'─'*60}\n"
        
        elif job['estado'] == 'iniciando':
            estado_msg += f"\n⏳ Iniciando scraper, espera un momento...\n"
        
        return estado_msg
    
    else:
        # Mostrar todos los trabajos
        if not jobs:
            return "📭 No hay trabajos de scraping en ejecución o completados."
        
        resumen = f"""{'='*60}
{'LISTA DE TRABAJOS':^60}
{'='*60}

"""
        for jid, job in sorted(jobs.items(), key=lambda x: x[1]['iniciado_en'], reverse=True):
            icono = {
                'iniciando': '🔄',
                'ejecutando': '⚙️',
                'completado': '✅',
                'cancelado': '🛑',
                'error': '❌'
            }.get(job['estado'], '❓')
            
            resumen += f"{icono} {jid}: {job['estado']} - {job['articulos']} artículos\n"
            resumen += f"   Iniciado: {job['iniciado_en']}\n\n"
        
        resumen += f"{'─'*60}\n"
        resumen += f"💡 Para ver detalles de un trabajo:\n"
        resumen += f"   obtener_estado_scraper(job_id=\"ID\")\n"
        
        return resumen


@mcp.tool()
async def detener_scraper(job_id: str) -> str:
    """
    Detiene un trabajo de scraping en ejecución.
    
    Args:
        job_id: ID del trabajo a detener
    
    Returns:
        Mensaje confirmando la detención del trabajo.
    """
    if job_id not in jobs:
        return f"❌ No se encontró el trabajo con ID: {job_id}"
    
    job = jobs[job_id]
    
    if job['estado'] not in ['iniciando', 'ejecutando']:
        return f"""ℹ️  El trabajo {job_id} no está en ejecución.
        
Estado actual: {job['estado']}

Solo puedes detener trabajos que estén 'iniciando' o 'ejecutando'.
"""
    
    # Verificar si tenemos el proceso
    if job_id not in processes:
        return f"""⚠️  No se encontró el proceso para el trabajo {job_id}.
        
Es posible que el proceso ya haya terminado o no se haya registrado correctamente.
Verifica el estado con: obtener_estado_scraper(job_id="{job_id}")
"""
    
    try:
        process = processes[job_id]
        
        # Intentar terminar el proceso suavemente
        process.terminate()
        
        # Esperar un poco a que termine
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
            mensaje = "✅ Proceso terminado correctamente"
        except asyncio.TimeoutError:
            # Si no termina en 5 segundos, forzar la terminación
            process.kill()
            await process.wait()
            mensaje = "⚠️  Proceso forzado a terminar (kill)"
        
        # Actualizar estado del job
        jobs[job_id]["estado"] = "cancelado"
        jobs[job_id]["finalizado_en"] = datetime.now().isoformat()
        jobs[job_id]["error"] = "Detenido manualmente por el usuario"
        
        # Remover de procesos activos
        if job_id in processes:
            del processes[job_id]
        
        return f"""{'='*60}
{'SCRAPER DETENIDO':^60}
{'='*60}

{mensaje}

Job ID: {job_id}
Estado: cancelado
Artículos extraídos antes de detener: {job['articulos']}

El proceso ha sido detenido exitosamente.
"""
    
    except Exception as e:
        return f"❌ Error al detener el proceso: {str(e)}"


@mcp.tool()
async def leer_noticias_valora(
    archivo: str = None,
    sector: str = None,
    limite: int = None
) -> str:
    """
    Lee y filtra las noticias extraídas por el scraper.
    
    Args:
        archivo: Ruta del archivo JSON (opcional, usa el más reciente si no se especifica)
        sector: Filtrar por sector específico (opcional)
        limite: Número máximo de noticias a retornar (opcional)
    
    Returns:
        JSON con las noticias filtradas.
    """
    try:
        project_dir = Path(__file__).parent.parent
        
        # Si no se especifica archivo, buscar el más reciente
        if not archivo:
            json_files = list(project_dir.glob("noticias_valora_*.json"))
            if not json_files:
                return "No se encontraron archivos de noticias. Ejecuta el scraper primero."
            archivo = max(json_files, key=lambda p: p.stat().st_mtime)
        else:
            archivo = Path(archivo)
        
        # Leer el archivo
        with open(archivo, 'r', encoding='utf-8') as f:
            noticias = json.load(f)
        
        if not isinstance(noticias, list):
            noticias = [noticias]
        
        # Filtrar por sector si se especifica
        if sector:
            noticias = [n for n in noticias if sector in n.get('sectores', [])]
        
        # Limitar cantidad
        if limite:
            noticias = noticias[:limite]
        
        return json.dumps(noticias, ensure_ascii=False, indent=2)
    
    except FileNotFoundError:
        return f"Archivo no encontrado: {archivo}"
    except Exception as e:
        return f"Error al leer noticias: {str(e)}"


@mcp.tool()
async def analizar_sentimiento_empresas_bvc(
    archivo: Optional[str] = None,
    output_file: Optional[str] = None
) -> str:
    """
    Analiza las noticias para identificar empresas de la BVC mencionadas
    y realiza análisis de sentimiento de cada noticia relacionada con cada empresa.
    
    Args:
        archivo: Ruta del archivo JSON de noticias (opcional, usa el más reciente)
        output_file: Ruta del archivo donde guardar el análisis (opcional)
    
    Returns:
        Resumen del análisis de sentimiento por empresa.
        
    Raises:
        FileNotFoundError: Si no se encuentra el archivo de noticias
        json.JSONDecodeError: Si el archivo JSON está corrupto
    """
    try:
        logger.info(f"Iniciando análisis de sentimiento. Archivo: {archivo or 'más reciente'}")
        
        # Importar las funciones de detección de empresas
        project_dir = Path(__file__).parent.parent
        scraper_path = project_dir / "scraper"
        if str(scraper_path) not in sys.path:
            sys.path.insert(0, str(scraper_path))
        
        from empresas_bvc import buscar_empresas_en_texto, obtener_info_empresa, EMPRESAS_BVC
        
        # Si no se especifica archivo, buscar el más reciente
        if not archivo:
            json_files = list(project_dir.glob("noticias_valora_*.json"))
            if not json_files:
                return "❌ No se encontraron archivos de noticias. Ejecuta el scraper primero."
            archivo = max(json_files, key=lambda p: p.stat().st_mtime)
        else:
            archivo = Path(archivo)
        
        # Leer las noticias
        with open(archivo, 'r', encoding='utf-8') as f:
            noticias = json.load(f)
        
        if not isinstance(noticias, list):
            noticias = [noticias]
        
        # Palabras clave para análisis de sentimiento
        palabras_positivas = [
            'crecimiento', 'aumento', 'éxito', 'ganancia', 'beneficio', 'inversión',
            'expansión', 'mejora', 'récord', 'avance', 'positivo', 'fortalece',
            'impulsa', 'optimismo', 'recuperación', 'incremento', 'alza', 'subió',
            'logro', 'sube', 'nueva planta', 'nuevo proyecto', 'contrato', 'adjudica',
            'rentabilidad', 'utilidad', 'dividendo', 'mayor', 'superó', 'supera',
            'destaca', 'lidera', 'liderazgo'
        ]
        
        palabras_negativas = [
            'crisis', 'pérdida', 'caída', 'disminución', 'reducción', 'problema',
            'dificultad', 'riesgo', 'amenaza', 'recorte', 'despido', 'cierre',
            'baja', 'bajó', 'cae', 'cayó', 'negativo', 'preocupación', 'incertidumbre',
            'débil', 'debilidad', 'deterioro', 'menor', 'multa', 'sanción',
            'demanda', 'controversia', 'investigación', 'pérdidas', 'declive'
        ]
        
        # Diccionario para acumular análisis por empresa
        analisis_empresas = {}
        
        # Analizar cada noticia
        for noticia in noticias:
            # Extraer el texto completo de la noticia
            titulo = noticia.get('titulo', '')
            contenido = noticia.get('contenido', '')
            texto_completo = f"{titulo} {contenido}".lower()
            
            # Buscar empresas mencionadas
            tickers_encontrados = buscar_empresas_en_texto(texto_completo)
            
            # Para cada empresa encontrada, analizar sentimiento
            for ticker in tickers_encontrados:
                info_empresa = obtener_info_empresa(ticker)
                
                if ticker not in analisis_empresas:
                    analisis_empresas[ticker] = {
                        'ticker': ticker,
                        'nombre': info_empresa['nombre_completo'],
                        'sector': info_empresa['sector'],
                        'noticias': [],
                        'sentimiento_agregado': {
                            'positivas': 0,
                            'negativas': 0,
                            'neutrales': 0
                        }
                    }
                
                # Análisis de sentimiento de esta noticia específica
                score_positivo = sum(1 for palabra in palabras_positivas if palabra in texto_completo)
                score_negativo = sum(1 for palabra in palabras_negativas if palabra in texto_completo)
                
                # Determinar sentimiento
                if score_positivo > score_negativo:
                    sentimiento = 'POSITIVO'
                    analisis_empresas[ticker]['sentimiento_agregado']['positivas'] += 1
                elif score_negativo > score_positivo:
                    sentimiento = 'NEGATIVO'
                    analisis_empresas[ticker]['sentimiento_agregado']['negativas'] += 1
                else:
                    sentimiento = 'NEUTRAL'
                    analisis_empresas[ticker]['sentimiento_agregado']['neutrales'] += 1
                
                # Agregar noticia con su análisis
                analisis_empresas[ticker]['noticias'].append({
                    'titulo': noticia.get('titulo', ''),
                    'url': noticia.get('url', ''),
                    'fecha': noticia.get('fecha', ''),
                    'sentimiento': sentimiento,
                    'score_positivo': score_positivo,
                    'score_negativo': score_negativo
                })
        
        # Calcular valoración final por empresa
        resultado_final = []
        for ticker, data in analisis_empresas.items():
            total_noticias = len(data['noticias'])
            positivas = data['sentimiento_agregado']['positivas']
            negativas = data['sentimiento_agregado']['negativas']
            neutrales = data['sentimiento_agregado']['neutrales']
            
            # Determinar valoración general
            if positivas > negativas + neutrales * 0.5:
                valoracion = 'POSITIVA'
            elif negativas > positivas + neutrales * 0.5:
                valoracion = 'NEGATIVA'
            else:
                valoracion = 'NEUTRAL'
            
            # Calcular porcentajes
            pct_positivo = round((positivas / total_noticias) * 100, 1) if total_noticias > 0 else 0
            pct_negativo = round((negativas / total_noticias) * 100, 1) if total_noticias > 0 else 0
            pct_neutral = round((neutrales / total_noticias) * 100, 1) if total_noticias > 0 else 0
            
            resultado_final.append({
                'ticker': data['ticker'],
                'empresa': data['nombre'],
                'sector': data['sector'],
                'valoracion': valoracion,
                'total_noticias': total_noticias,
                'analisis_sentimiento': {
                    'positivas': positivas,
                    'negativas': negativas,
                    'neutrales': neutrales,
                    'porcentaje_positivo': pct_positivo,
                    'porcentaje_negativo': pct_negativo,
                    'porcentaje_neutral': pct_neutral
                },
                'noticias': data['noticias']
            })
        
        # Ordenar por número de noticias (más mencionadas primero)
        resultado_final.sort(key=lambda x: x['total_noticias'], reverse=True)
        
        # Guardar en archivo si se especifica
        if output_file:
            output_path = Path(output_file)
        else:
            output_path = project_dir / "analisis_empresas_bvc.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(resultado_final, f, ensure_ascii=False, indent=2)
        
        # Crear resumen legible
        resumen = f"""{'='*70}
{'ANÁLISIS DE SENTIMIENTO - EMPRESAS BVC':^70}
{'='*70}

📊 Total de empresas encontradas: {len(resultado_final)}
📰 Total de noticias analizadas: {len(noticias)}
💾 Archivo generado: {output_path.name}

{'─'*70}
"""
        
        if resultado_final:
            resumen += "\n📈 EMPRESAS IDENTIFICADAS Y SU VALORACIÓN:\n\n"
            
            for empresa in resultado_final:
                icono = {
                    'POSITIVA': '🟢',
                    'NEGATIVA': '🔴',
                    'NEUTRAL': '🟡'
                }[empresa['valoracion']]
                
                resumen += f"{icono} {empresa['empresa']} ({empresa['ticker']})\n"
                resumen += f"   Sector: {empresa['sector']}\n"
                resumen += f"   Valoración: {empresa['valoracion']}\n"
                resumen += f"   Noticias: {empresa['total_noticias']} total "
                resumen += f"({empresa['analisis_sentimiento']['positivas']}+ / "
                resumen += f"{empresa['analisis_sentimiento']['negativas']}- / "
                resumen += f"{empresa['analisis_sentimiento']['neutrales']}≈)\n"
                resumen += f"   Distribución: {empresa['analisis_sentimiento']['porcentaje_positivo']}% pos / "
                resumen += f"{empresa['analisis_sentimiento']['porcentaje_negativo']}% neg / "
                resumen += f"{empresa['analisis_sentimiento']['porcentaje_neutral']}% neu\n\n"
        else:
            resumen += "\n⚠️  No se identificaron empresas de la BVC en las noticias.\n"
            resumen += "   Verifica que las noticias contengan menciones a empresas colombianas.\n"
        
        resumen += f"{'─'*70}\n"
        resumen += f"\n💡 El análisis completo en JSON está disponible en:\n"
        resumen += f"   {output_path}\n"
        resumen += f"\n📋 Total empresas registradas en BVC: {len(EMPRESAS_BVC)}\n"
        
        return resumen
        
    except Exception as e:
        return f"❌ Error al analizar sentimiento: {str(e)}"



# =====================================================================
# SEGUNDA SESIÓN - ANÁLISIS FUNDAMENTAL Y FINANCIERO
# =====================================================================

@mcp.tool()
async def obtener_datos_financieros(ticker: str) -> dict:
    """
    Extrae indicadores financieros detallados (EBITDA, Cashflow, Ratios) para un ticker.
    
    INSTRUCCIONES DE ANALISTA SENIOR:
    Una vez que recibas los datos de esta herramienta, NO te limites a exponer los números.
    Actúa como un Analista de Inversiones con 20 años de experiencia:
    1. Interpreta la salud financiera de la empresa comparando los ratios con el sector.
    2. Identifica banderas rojas (ej: deuda alta vs flujo de caja débil).
    3. Concluye con un resumen ejecutivo sobre la tesis de inversión.
    4. Mantén un tono profesional, crítico y riguroso.
    
    Args:
        ticker: El símbolo bursátil de la empresa (ej: 'ECOPETROL.CL' o el ticker correspondiente).
    """
    try:
        # Inicializar el ticker
        empresa = yf.Ticker(ticker)
        
        # Obtener toda la información disponible
        info = empresa.info
        
        # Filtramos o preparamos los datos clave para que sean más legibles
        # Si prefieres devolver 'todo', puedes simplemente devolver 'info'
        datos_clave = {
            "nombre": info.get("longName"),
            "precio_actual": info.get("currentPrice") or info.get("regularMarketPrice"),
            "moneda": info.get("currency"),
            "ebitda": info.get("ebitda"),
            "cashflow_operativo": info.get("operatingCashflow"),
            "free_cashflow": info.get("freeCashflow"),
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector"),
            "industria": info.get("industry")
        }
        
        return datos_clave
        
    except Exception as e:
        return {"error": f"No se pudo obtener la información para {ticker}: {str(e)}"}
    

if __name__ == "__main__":
    # Iniciar el servidor MCP
    mcp.run()

