#!/usr/bin/env python3
import json

try:
    with open('noticias_valora_5dias_test.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f'✅ JSON válido! Total de noticias: {len(data)}')
    print(f'\nPrimera noticia:')
    print(f'  Título: {data[0]["titulo"][:80]}...')
    print(f'  Fecha: {data[0]["fecha"]}')
    print(f'  Sectores: {data[0]["sectores"]}')
except json.JSONDecodeError as e:
    print(f'❌ Error JSON en línea {e.lineno}, columna {e.colno}')
    print(f'Mensaje: {e.msg}')
    
    # Mostrar contexto
    with open('noticias_valora_5dias_test.json', 'r', encoding='utf-8') as f:
        content = f.read()
        start = max(0, e.pos - 200)
        end = min(len(content), e.pos + 200)
        print(f'\nContexto del error:')
        print(repr(content[start:end]))
except Exception as e:
    print(f'❌ Error: {e}')
