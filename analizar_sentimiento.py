#!/usr/bin/env python3
"""
Script para analizar sentimiento de empresas de la BVC en noticias scraped.
"""
import json
import sys
from pathlib import Path

# Agregar el directorio scraper al path
sys.path.insert(0, str(Path(__file__).parent / "scraper"))

from empresas_bvc import buscar_empresas_en_texto, obtener_info_empresa, EMPRESAS_BVC

# Palabras clave para análisis de sentimiento
PALABRAS_POSITIVAS = [
    'crecimiento', 'aumento', 'éxito', 'ganancia', 'beneficio', 'inversión',
    'expansión', 'mejora', 'récord', 'avance', 'positivo', 'fortalece',
    'impulsa', 'optimismo', 'recuperación', 'incremento', 'alza', 'subió',
    'logro', 'sube', 'nueva planta', 'nuevo proyecto', 'contrato', 'adjudica',
    'rentabilidad', 'utilidad', 'dividendo', 'mayor', 'superó', 'supera',
    'destaca', 'lidera', 'liderazgo',  'sólido', 'robusto', 'favorable'
]

PALABRAS_NEGATIVAS = [
    'crisis', 'pérdida', 'caída', 'disminución', 'reducción', 'problema',
    'dificultad', 'riesgo', 'amenaza', 'recorte', 'despido', 'cierre',
    'baja', 'bajó', 'cae', 'cayó', 'negativo', 'preocupación', 'incertidumbre',
    'débil', 'debilidad', 'deterioro', 'menor', 'multa', 'sanción',
    'demanda', 'controversia', 'investigación', 'pérdidas', 'declive', 
    'afectación', 'impacto negativo', 'presión'
]

def main():
    # Leer las noticias
    archivo = Path('noticias_valora_5dias.json')
    
    if not archivo.exists():
        print('❌ No se encontró el archivo de noticias.')
        return
    
    with open(archivo, 'r', encoding='utf-8') as f:
        noticias = json.load(f)
    
    print(f'📰 Analizando {len(noticias)} noticias...\n')
    
    # Diccionario para acumular análisis por empresa
    analisis_empresas = {}
    
    # Analizar cada noticia
    for noticia in noticias:
        # Extraer el texto completo
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
            
            # Análisis de sentimiento
            score_positivo = sum(1 for palabra in PALABRAS_POSITIVAS if palabra in texto_completo)
            score_negativo = sum(1 for palabra in PALABRAS_NEGATIVAS if palabra in texto_completo)
            
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
            
            # Agregar noticia
            analisis_empresas[ticker]['noticias'].append({
                'titulo': noticia.get('titulo', ''),
                'url': noticia.get('url', ''),
                'fecha': noticia.get('fecha', ''),
                'sentimiento': sentimiento,
                'score_positivo': score_positivo,
                'score_negativo': score_negativo
            })
    
    # Calcular valoración final
    resultado_final = []
    for ticker, data in analisis_empresas.items():
        total_noticias = len(data['noticias'])
        positivas = data['sentimiento_agregado']['positivas']
        negativas = data['sentimiento_agregado']['negativas']
        neutrales = data['sentimiento_agregado']['neutrales']
        
        # Determinar valoración
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
    
    # Ordenar por número de noticias
    resultado_final.sort(key=lambda x: x['total_noticias'], reverse=True)
    
    # Guardar JSON
    output_path = Path('analisis_empresas_bvc.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=2)
    
    # Mostrar resumen
    print(f'{'='*70}')
    print(f'{'ANÁLISIS DE SENTIMIENTO - EMPRESAS BVC':^70}')
    print(f'{'='*70}\n')
    print(f'📊 Total de empresas encontradas: {len(resultado_final)}')
    print(f'📰 Total de noticias analizadas: {len(noticias)}')
    print(f'💾 Archivo generado: {output_path.name}\n')
    print(f'{'─'*70}\n')
    
    if resultado_final:
        print('📈 EMPRESAS IDENTIFICADAS Y SU VALORACIÓN:\n')
        
        for empresa in resultado_final:
            icono = {
                'POSITIVA': '🟢',
                'NEGATIVA': '🔴',
                'NEUTRAL': '🟡'
            }[empresa['valoracion']]
            
            print(f"{icono} {empresa['empresa']} ({empresa['ticker']})")
            print(f"   Sector: {empresa['sector']}")
            print(f"   Valoración: {empresa['valoracion']}")
            print(f"   Noticias: {empresa['total_noticias']} total "
                  f"({empresa['analisis_sentimiento']['positivas']}+ / "
                  f"{empresa['analisis_sentimiento']['negativas']}- / "
                  f"{empresa['analisis_sentimiento']['neutrales']}≈)")
            print(f"   Distribución: {empresa['analisis_sentimiento']['porcentaje_positivo']}% pos / "
                  f"{empresa['analisis_sentimiento']['porcentaje_negativo']}% neg / "
                  f"{empresa['analisis_sentimiento']['porcentaje_neutral']}% neu\n")
    else:
        print('⚠️  No se identificaron empresas de la BVC en las noticias.\n')
    
    print(f'{'─'*70}')
    print(f'\n💡 El análisis completo en JSON está disponible en: {output_path}')
    print(f'\n📋 Total empresas registradas en BVC: {len(EMPRESAS_BVC)}')

if __name__ == '__main__':
    main()
