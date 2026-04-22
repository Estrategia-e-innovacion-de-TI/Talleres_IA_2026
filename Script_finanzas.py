def calcular_ratios(datos):
    """
    Calcula ratios financieros clave a partir de un diccionario de datos de empresa.
    Espera las siguientes claves: ingresos, costos_operativos, depreciacion, amortizacion,
    utilidad_neta, flujo_operativo, capex, acciones_en_circulacion, precio_accion, patrimonio.
    """

    # Para Celsia
    # EBITDA
    ebitda = datos['utilidad_neta'] + datos['depreciacion comparada'] + datos.get('gastos_interes', 0) + datos.get('impuestos', 0)
    # Flujo Operativo
    flujo_operativo = datos['flujo_operativo']
    # Free Cash Flow
    free_cash_flow = flujo_operativo - datos['capex']
    # P/E Ratio
    eps = datos['utilidad_neta'] / datos['acciones_en_circulacion']
    pe_ratio = datos['precio_accion'] / eps if eps != 0 else None
    # ROE
    roe = datos['utilidad_neta'] / datos['patrimonio'] if datos['patrimonio'] != 0 else None
    # Margen Neto
    margen_neto = datos['utilidad_neta'] / datos['ingresos'] if datos['ingresos'] != 0 else None

    return {
        'EBITDA': ebitda,
        'Flujo Operativo': flujo_operativo,
        'Free Cash Flow': free_cash_flow,
        'P/E Ratio': pe_ratio,
        'ROE': roe,
        'Margen Neto': margen_neto
    }

# Ejemplo de uso:
datos_empresa = {
    'ingresos': 5395120000, 
    'costos_operativos': 389418000, #gastos operativos
    'depreciacion comparada': 439415000, 
    'utilidad_neta': 359634000, # ingresos netos de operaciones continuas
    'flujo_operativo': 2018706000,
    'capex': -1331834000, # Inversiones en bienes de capital
    'acciones_en_circulacion': 1032915.62, 
    'precio_accion': 5490,
    'patrimonio': 3421272000,
    'gastos_interes': 602388000,
    'impuestos': 178678000 #Provisión de impuestos
}

ratios = calcular_ratios(datos_empresa)
for k, v in ratios.items():
    print(f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}")