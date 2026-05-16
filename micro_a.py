import oracledb
import re
from datetime import datetime
from cryptography.fernet import Fernet

# --- CONFIGURACIÓN ÉTICA ---
key = Fernet.generate_key()
cipher_suite = Fernet(key)

def cifrar_dato(dato):
    if not dato or dato == "NO DISPONIBLE": return dato
    return cipher_suite.encrypt(str(dato).encode()).decode()

# --- REGLAS DE NEGOCIO CRÍTICAS ---
def normalizar_rut(rut):
    if not rut: return None
    limpio = re.sub(r'[^0-9kK]', '', str(rut))
    if len(limpio) < 8: 
        return "XX.XXX.XXX-X"
    cuerpo = limpio[:-1]
    dv = limpio[-1].upper()
    cuerpo_fmt = f"{int(cuerpo):,}".replace(",", ".")
    return f"{cuerpo_fmt}-{dv}"

def separar_nombre(nombre_completo):
    nombre_limpio = (nombre_completo or "").replace(",", " ").strip()
    partes = nombre_limpio.split()
    if len(partes) >= 3:
        return partes[0], partes[1], partes[2]
    elif len(partes) == 2:
        return partes[0], partes[1], "NO DISPONIBLE"
    return (partes[0] if partes else "NO DISPONIBLE"), "NO DISPONIBLE", "NO DISPONIBLE"

def normalizar_texto(texto):
    if not texto or texto == "NO DISPONIBLE": return "NO DISPONIBLE"
    texto = str(texto).strip()
    
    palabras_rotas = {
        'Ins': 'Ines', 'Coln': 'Colon', 'Rentera': 'Renteria', 
        'Maipu': 'Maipu', 'Maip': 'Maipu', 'Martnez': 'Martinez', 
        'San Martn': 'San Martin', 'Valparaso': 'Valparaiso', 
        'Machal': 'Machali', 'Hualpn': 'Hualpen', 'Chilln': 'Chillan', 
        'Gonzlez': 'Gonzalez', 'Peaflor': 'Penaflor', 'Luca': 'Lucia', 
        'Larran': 'Larrain', 'Bermdez': 'Bermudez', 'Chvez': 'Chavez', 
        'Ros': 'Rios', 'Jos': 'Jose', 'Agustn': 'Agustin', 
        'Bentez': 'Benitez', 'Estefana': 'Estefania', 'Pea': 'Pena',
        'Artigas': 'Artigas'
    }
    
    for rota, corregida in palabras_rotas.items():
        texto = texto.replace(rota, corregida)
        
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'ñ': 'n', 'Ñ': 'N'
    }
    for con_tilde, sin_tilde in reemplazos.items():
        texto = texto.replace(con_tilde, sin_tilde)
        
    return texto

def parsear_fecha(fecha_raw):
    fecha_iso = datetime.now().strftime('%Y-%m-%d')
    fecha_dt = datetime.now()
    if fecha_raw:
        formatos = ['%m%d%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y', '%m-%d-%Y']
        exito = False
        if isinstance(fecha_raw, datetime):
            fecha_dt = fecha_raw
            fecha_iso = fecha_dt.strftime('%Y-%m-%d')
            exito = True
        else:
            for fmt in formatos:
                try:
                    fecha_dt = datetime.strptime(str(fecha_raw).strip(), fmt)
                    fecha_iso = fecha_dt.strftime('%Y-%m-%d')
                    exito = True
                    break
                except ValueError:
                    continue
    return fecha_iso, fecha_dt

def extraer_y_validar():
    conn = oracledb.connect(user="Eva2_PID", password="Eva2_PID", dsn="localhost:1521/XEPDB1")
    cursor = conn.cursor()
    
    # 1. LEER TRANSACCIONES PRIMERO
    cursor.execute("SELECT TRANSACCIONID, IDCLIENTE, MONTO, FECHATRANSACCION, DETALLE FROM TRANSACCIONES")
    rows_transacciones = cursor.fetchall()
    
    tx_fechas = {}
    transacciones_raw_list = []
    
    for row in rows_transacciones:
        t_id, c_id, monto, f_raw, detalle = row
        f_iso, f_dt = parsear_fecha(f_raw)
        transacciones_raw_list.append((t_id, c_id, monto, f_iso, detalle, f_dt))
        
        if c_id not in tx_fechas or f_dt > tx_fechas[c_id]:
            tx_fechas[c_id] = f_dt

    # 2. LEER CLIENTES
    cursor.execute("SELECT IDCLIENTE, RUT, NOMBRE, EMAIL, TELEFONO, FECHAREGISTRO, DIRECCION, CIUDAD, CODIGOPOSTAL FROM CLIENTES")
    rows_clientes = cursor.fetchall()
    
    stats = {
        "total_clientes": len(rows_clientes),
        "clientes_descartados": 0,
        "clientes_duplicados": 0,
        "clientes_transformados": 0,
        "clientes_sin_cambios": 0,
        "transacciones_totales": len(rows_transacciones),
        "transacciones_migradas": 0
    }
    
    clientes_filtrados = {}
    
    for row in rows_clientes:
        id_cliente, rut_raw, nombre_raw, email_raw, tel_raw, fecha_raw, dir_raw, ciu_raw, cp_raw = row
        
        if not rut_raw:
            stats["clientes_descartados"] += 1
            continue 

        rut_fmt = normalizar_rut(rut_raw)
        fecha_iso, fecha_dt_cliente = parsear_fecha(fecha_raw)
        fecha_ref = tx_fechas.get(id_cliente, fecha_dt_cliente)
        
        nom, pat, mat = separar_nombre(nombre_raw)
        nom, pat, mat = normalizar_texto(nom), normalizar_texto(pat), normalizar_texto(mat)
        direccion_fmt = normalizar_texto(dir_raw)
        ciudad_fmt = normalizar_texto(ciu_raw)
        cp_fmt = cp_raw if cp_raw else "0000"
        
        email_cif = cifrar_dato(email_raw or "NO DISPONIBLE")
        tel_cif = cifrar_dato(tel_raw or "NO DISPONIBLE")

        nuevo_cliente_tuple = (
            id_cliente, rut_fmt, nom, pat, mat, tel_cif, email_cif, 
            direccion_fmt, ciudad_fmt, cp_fmt, fecha_iso
        )
        
        # Evaluación de transformación estructural (Rúbrica Dimensión 3)
        se_transformo = (rut_raw != rut_fmt) or (nombre_raw != f"{nom} {pat} {mat}".strip().replace(" NO DISPONIBLE", "")) or (not dir_raw) or (not ciu_raw)
        
        if rut_fmt in clientes_filtrados:
            stats["clientes_duplicados"] += 1
            if fecha_ref > clientes_filtrados[rut_fmt]['fecha_ref']:
                clientes_filtrados[rut_fmt] = {
                    'data': nuevo_cliente_tuple,
                    'fecha_ref': fecha_ref,
                    'id_cliente': id_cliente,
                    'transformed': se_transformo
                }
        else:
            clientes_filtrados[rut_fmt] = {
                'data': nuevo_cliente_tuple,
                'fecha_ref': fecha_ref,
                'id_cliente': id_cliente,
                'transformed': se_transformo
            }

    # Desempaquetar y calcular estadísticas finales consolidadas
    clientes_listos = []
    ids_clientes_validos = set()
    for item in clientes_filtrados.values():
        clientes_listos.append(item['data'])
        ids_clientes_validos.add(item['id_cliente'])
        if item['transformed']:
            stats["clientes_transformados"] += 1
        else:
            stats["clientes_sin_cambios"] += 1

    # 3. FILTRAR TRANSACCIONES FINALES
    transacciones_listas = []
    for t_id, c_id, monto, f_iso, detalle, f_dt in transacciones_raw_list:
        if c_id in ids_clientes_validos:
            transacciones_listas.append((t_id, c_id, monto, f_iso, normalizar_texto(detalle)))
            stats["transacciones_migradas"] += 1

    conn.close()
    return clientes_listos, transacciones_listas, stats