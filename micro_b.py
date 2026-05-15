import oracledb

def cargar_datos(datos):
    try:
        conn = oracledb.connect(user="Eva2_PID", password="Eva2_PID", dsn="localhost:1521/XEPDB1")
        cursor = conn.cursor()

    	# Paso 1: Limpieza cumpliendo integridad referencial
        print("Limpiando tablas de destino...")
        cursor.execute("DELETE FROM TRANSACCIONES")
        cursor.execute("DELETE FROM CLIENTES")

        # Paso 2: Inserción Masiva (Eficiencia 5%)
        sql = """INSERT INTO CLIENTES 
                 (IDCLIENTE, RUT, NOMBRE, APELLIDOPATERNO, APELLIDOMATERNO, 
                  TELEFONO, EMAIL, DIRECCION, CIUDAD, CODIGOPOSTAL, FECHAREGISTRO) 
                 VALUES (:1, :2, :3, :4, :5, :6, :7, :8, :9, :10, :11)"""
        
        cursor.executemany(sql, datos)
        conn.commit()
        print(f"✅ MIGRACIÓN EXITOSA: {cursor.rowcount} registros insertados.")
        
    except Exception as e:
        print(f"❌ Error crítico en Microservicio B: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    from micro_a import extraer_y_validar
    print("--- Iniciando Proceso de Microservicios ---")
    lista_limpia = extraer_y_validar()
    if lista_limpia:
        cargar_datos(lista_limpia)