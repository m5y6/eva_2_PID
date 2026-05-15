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

def normalizar_rut(rut):
    if not rut: return None
    limpio = re.sub(r'[^0-9kK]', '', str(rut))
    if len(limpio) < 8: return None
    cuerpo = limpio[:-1]
    dv = limpio[-1].upper()
    return f"{int(cuerpo):,}.{dv}".replace(",", ".")

def separar_nombre(nombre_completo):
    partes = (nombre_completo or "").strip().split()
    if len(partes) >= 3:
        return partes[0], partes[1], partes[2]
    elif len(partes) == 2:
        return partes[0], partes[1], "NO DISPONIBLE"
    return (partes[0] if partes else "NO DISPONIBLE"), "NO DISPONIBLE", "NO DISPONIBLE"

def extraer_y_validar():
    # Conexión a la PDB correcta
    conn = oracledb.connect(user="Eva2_PID", password="Eva2_PID", dsn="localhost:1521/XEPDB1")
    cursor = conn.cursor()
    
    # Consulta a la tabla origen
    cursor.execute("SELECT RUT, NOMBRE, EMAIL, TELEFONO, FECHAREGISTRO FROM CLIENTES")
    rows = cursor.fetchall()
    print(f"DEBUG: Se encontraron {len(rows)} filas en la tabla de origen.")
    
    datos_listos = []
    ruts_vistos = {}
    id_contador = 1 

    for row in rows:
        rut_raw, nombre_raw, email_raw, tel_raw, fecha_raw = row
        
        # 1. Normalizar RUT
        rut_fmt = normalizar_rut(rut_raw)
        if not rut_fmt: continue 

        # 2. Lógica de Fecha Robusta (NUEVA VERSIÓN MULTI-FORMATO)
        fecha_iso = datetime.now().strftime('%Y-%m-%d') # Por defecto hoy
        fecha_dt = datetime.now()
        
        if fecha_raw:
            # Lista de formatos que el profe Eric podría haber usado
            formatos = ['%m%d%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y']
            exito_fecha = False
            
            if isinstance(fecha_raw, datetime):
                fecha_dt = fecha_raw
                fecha_iso = fecha_dt.strftime('%Y-%m-%d')
                exito_fecha = True
            else:
                for fmt in formatos:
                    try:
                        fecha_dt = datetime.strptime(str(fecha_raw).strip(), fmt)
                        fecha_iso = fecha_dt.strftime('%Y-%m-%d')
                        exito_fecha = True
                        break # Si lo logra con uno, deja de intentar
                    except ValueError:
                        continue
            
            if not exito_fecha:
                print(f"⚠️ Fecha ilegible persistente: {fecha_raw}. Usando fecha actual.")
        
        # 3. Manejo de Duplicados (Mantener el más reciente)
        if rut_fmt in ruts_vistos and fecha_dt <= ruts_vistos[rut_fmt]: 
            continue
        
        # 4. Transformaciones y Ética (Cifrado)
        nom, pat, mat = separar_nombre(nombre_raw)
        email_cif = cifrar_dato(email_raw or "NO DISPONIBLE")
        tel_cif = cifrar_dato(tel_raw or "NO DISPONIBLE")

        # 5. Preparar para Microservicio B
        datos_listos.append((
            id_contador, rut_fmt, nom, pat, mat, tel_cif, email_cif, 
            "DIRECCION NO DISPONIBLE", "CIUDAD NO DISPONIBLE", "0000", 
            fecha_iso
        ))
        
        ruts_vistos[rut_fmt] = fecha_dt
        id_contador += 1

    conn.close()
    return datos_listos