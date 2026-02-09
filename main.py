"""
Microservicio para impresión de etiquetas RFID - Printronix AUTO ID T820
"""

import socket
import asyncio
import base64
from typing import List
from contextlib import asynccontextmanager

from firebird.driver import connect, driver_config
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# Configuración de la impresora RFID
PRINTER_IP = "192.168.1.150"
PRINTER_PORT = 9100

# Configuración de la base de datos Firebird
FIREBIRD_CONFIG = {
    "host": "localhost",
    "database": "C:/laragon/www/amparv3/bd/AMPARJUL.FDB",  
    "user": "SYSDBA",
    "password": "masterkey",  
    "charset": "UTF8",
}

# URL base para el QR
QR_BASE_URL = "http://b8ff0b49f137.sn.mynetname.net:81/amparv3/gui/remisiones.carrito.php?stockid="

# Delay entre impresiones (segundos)
PRINT_DELAY = 0.5


# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class FolioRequest(BaseModel):
    """Modelo para una solicitud de impresión de un folio"""
    folio: str = Field(..., description="Folio en formato 'A00219-25'", example="A00219-25")


class MultipleFoliosRequest(BaseModel):
    """Modelo para solicitud de impresión de múltiples folios"""
    folios: List[str] = Field(
        ..., 
        description="Lista de folios en formato 'A00219-25'",
        example=["A00219-25", "A00220-25", "A00221-25"]
    )


class PrintResponse(BaseModel):
    """Modelo de respuesta de impresión"""
    success: bool
    message: str
    folio: str
    folio_sin_guion: str


class MultiplePrintResponse(BaseModel):
    """Modelo de respuesta para múltiples impresiones"""
    success: bool
    message: str
    total_folios: int
    resultados: List[PrintResponse]


# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def get_db_connection():
    """Obtiene una conexión a la base de datos Firebird"""
    try:
        conn = connect(
            f"{FIREBIRD_CONFIG['host']}:{FIREBIRD_CONFIG['database']}",
            user=FIREBIRD_CONFIG["user"],
            password=FIREBIRD_CONFIG["password"],
            charset=FIREBIRD_CONFIG["charset"],
        )
        return conn
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al conectar con la base de datos: {str(e)}"
        )


def buscar_folio_en_db(folio: str) -> dict | None:
    """
    Busca un folio en la tabla AMPAR_HIS_STOCK con toda la información relacionada
    
    Args:
        folio: El folio a buscar (con guión, ej: 'A00219-25')
    
    Returns:
        dict con los datos del registro o None si no existe
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Consulta directa desde STOCK usando STOCK_ESDETID y STOCK_ALMACENIDACTUAL
        sql = """
            SELECT 
                ST.STOCK_ID,
                ST.STOCK_FOLIO,
                ST.STOCK_LOTE,
                ST.STOCK_CADUCIDAD,
                ST.STOCK_ESDETID,
                ST.STOCK_ALMACENIDACTUAL,
                ED.ESDET_LOTE,
                ED.ESDET_CADUCIDAD,
                ED.ESDET_SERIE,
                ED.ESDET_ARTICULOID,
                A.ALMACEN_ID,
                A.ALMACEN_NOMBRE,
                SU.SUCURSAL_ID,
                SU.NOMBRE AS SUCURSAL_NOMBRE,
                AR.NOMBRE AS ARTICULO_NOMBRE,
                X.CLAVE_ARTICULO
            FROM AMPAR_HIS_STOCK ST
            LEFT JOIN AMPAR_HIS_ESDET ED ON ED.ESDET_ID = ST.STOCK_ESDETID
            LEFT JOIN ARTICULOS AR ON AR.ARTICULO_ID = ED.ESDET_ARTICULOID
            LEFT JOIN (
                SELECT CLAVE_ARTICULO, ARTICULO_ID 
                FROM CLAVES_ARTICULOS 
                WHERE ROL_CLAVE_ART_ID = 17
            ) X ON X.ARTICULO_ID = AR.ARTICULO_ID
            LEFT JOIN AMPAR_HIS_ALMACEN A ON A.ALMACEN_ID = ST.STOCK_ALMACENIDACTUAL
            LEFT JOIN SUCURSALES SU ON SU.SUCURSAL_ID = A.ALMACEN_SUCURSAL_MS
            WHERE ST.STOCK_FOLIO = ?
        """
        cursor.execute(sql, (folio,))
        row = cursor.fetchone()
        
        if row:
            # Obtener nombres de columnas
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    finally:
        conn.close()


def actualizar_temp_etiqueta(folio: str, folio_sin_guion: str) -> bool:
    """
    Actualiza la columna STOCK_TEMPETIQUETA con el folio sin guión
    
    Args:
        folio: El folio original (con guión)
        folio_sin_guion: El folio sin guión
    
    Returns:
        True si se actualizó correctamente
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE AMPAR_HIS_STOCK SET STOCK_TEMPETIQUETA = ? WHERE STOCK_FOLIO = ?",
            (folio_sin_guion, folio)
        )
        conn.commit()
        # En firebird-driver, rowcount puede no ser confiable
        # Si llegamos aquí sin excepción, el UPDATE fue exitoso
        return True
    except Exception as e:
        conn.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar STOCK_TEMPETIQUETA: {str(e)}"
        )
    finally:
        conn.close()


# ============================================================================
# FUNCIONES DE IMPRESIÓN
# ============================================================================

def generar_zpl(folio_sin_guion: str, folio_original: str, registro: dict) -> str:
    """
    Genera el código ZPL para la etiqueta RFID 10cm x 5cm
    
    Args:
        folio_sin_guion: El folio sin guión para el RFID
        folio_original: El folio original con guión para el código de barras
        registro: Diccionario con todos los datos del registro
    
    Returns:
        Código ZPL formateado
    """
    # Convertir texto a HEX para EPC (12 bytes = 24 hex chars)
    rfid_hex = folio_sin_guion.encode("ascii").hex().upper()
    rfid_hex = rfid_hex.ljust(24, "0")[:24]
    
    # Extraer datos del registro (con valores por defecto si no existen)
    stock_folio = str(registro.get("STOCK_FOLIO", "") or "").strip()[:20]
    almacen_nombre = str(registro.get("ALMACEN_NOMBRE", "") or "").strip()[:22]
    sucursal_nombre = str(registro.get("SUCURSAL_NOMBRE", "") or "").strip()[:22]
    clave_articulo = str(registro.get("CLAVE_ARTICULO", "") or "").strip()[:25]
    articulo_nombre = str(registro.get("ARTICULO_NOMBRE", "") or "").strip()[:35]
    lote = str(registro.get("ESDET_LOTE") or registro.get("STOCK_LOTE", "") or "").strip()[:18]
    caducidad = str(registro.get("ESDET_CADUCIDAD") or registro.get("STOCK_CADUCIDAD", "") or "").strip()[:18]
    stock_id = registro.get("STOCK_ID", "")
    
    # Generar URL para QR con STOCK_ID en base64
    stock_id_b64 = base64.b64encode(str(stock_id).encode()).decode() if stock_id else ""
    qr_url = f"{QR_BASE_URL}{stock_id_b64}"
    
    # ZPL para etiqueta 10cm x 5cm (800 x 400 dots a 203 DPI)
    # Formato: STOCK_FOLIO, ALMACEN (SUCURSAL), CLAVE_ARTICULO, ARTICULO_NOMBRE, LOTE, CADUCIDAD
    zpl = f"""
^XA
^PW800
^LL400
^LH0,0

^RS8,,100,1,E,,,6^FS
^RFW,H,2,16,1^FD{rfid_hex}^FS

^FO20,20
^A0N,30,30
^FD{stock_folio}^FS

^FO20,55
^A0N,26,26
^FD{almacen_nombre} ({sucursal_nombre})^FS

^FO20,90
^A0N,24,24
^FD{clave_articulo}^FS

^FO20,120
^A0N,22,22
^FD{articulo_nombre}^FS

^FO20,155
^A0N,20,20
^FDLote: {lote}^FS

^FO20,180
^A0N,20,20
^FDCad: {caducidad}^FS

^FO20,220
^BCN,70,Y,N,N
^FD{folio_original}^FS

^FO480,30
^BQN,2,6
^FDQA,{qr_url}^FS

^PQ1
^XZ
"""
    return zpl


def enviar_a_impresora(zpl: str) -> bool:
    """
    Envía el código ZPL a la impresora
    
    Args:
        zpl: Código ZPL a enviar
    
    Returns:
        True si se envió correctamente
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)  # Timeout de 10 segundos
        s.connect((PRINTER_IP, PRINTER_PORT))
        s.sendall(zpl.encode("latin-1", errors="replace"))
        s.close()
        return True
    except socket.error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al conectar con la impresora: {str(e)}"
        )


async def imprimir_etiqueta(folio: str) -> PrintResponse:
    """
    Proceso completo de impresión de una etiqueta
    
    Args:
        folio: El folio en formato 'A00219-25'
    
    Returns:
        PrintResponse con el resultado de la operación
    """
    # Quitar el guión del folio
    folio_sin_guion = folio.replace("-", "")
    
    # Buscar el folio en la base de datos
    registro = buscar_folio_en_db(folio)
    if not registro:
        return PrintResponse(
            success=False,
            message=f"Folio '{folio}' no encontrado en la base de datos",
            folio=folio,
            folio_sin_guion=folio_sin_guion
        )
    
    # Actualizar STOCK_TEMPETIQUETA
    actualizar_temp_etiqueta(folio, folio_sin_guion)
    
    # Generar ZPL e imprimir
    zpl = generar_zpl(folio_sin_guion, folio, registro)
    enviado = enviar_a_impresora(zpl)
    
    if enviado:
        return PrintResponse(
            success=True,
            message=f"Etiqueta impresa correctamente para folio '{folio}'",
            folio=folio,
            folio_sin_guion=folio_sin_guion
        )
    else:
        return PrintResponse(
            success=False,
            message=f"Error al enviar la etiqueta a la impresora",
            folio=folio,
            folio_sin_guion=folio_sin_guion
        )


# ============================================================================
# APLICACIÓN FASTAPI
# ============================================================================

app = FastAPI(
    title="RFID Label Printing API",
    description="Microservicio para impresión de etiquetas RFID en impresora Printronix AUTO ID T820",
    version="1.0.0",
)

# Configurar CORS - Configuración permisiva para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_credentials=False,  # Debe ser False cuando allow_origins es "*"
    allow_methods=["*"],  # Permite todos los métodos (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],  # Permite todas las cabeceras
    expose_headers=["*"],  # Expone todas las cabeceras en la respuesta
    max_age=3600,  # Cache preflight por 1 hora
)

# Middleware adicional para asegurar headers CORS en todas las respuestas
@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Max-Age"] = "3600"
    return response


@app.get("/")
async def root():
    """Endpoint de salud del servicio"""
    return {
        "status": "ok",
        "service": "RFID Label Printing API",
        "printer_ip": PRINTER_IP,
        "printer_port": PRINTER_PORT
    }


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Manejador de preflight requests para CORS"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )


@app.get("/health")
async def health_check():
    """Verificación de salud del servicio"""
    return {"status": "healthy"}


@app.get("/consultar/{folio}")
async def consultar_folio(folio: str):
    """
    Consulta todos los datos disponibles de un folio en la base de datos
    
    - **folio**: El folio en formato 'A00219-25'
    
    Retorna todos los campos de la tabla AMPAR_HIS_STOCK para ese folio
    """
    registro = buscar_folio_en_db(folio)
    
    if not registro:
        raise HTTPException(
            status_code=404,
            detail=f"Folio '{folio}' no encontrado en la base de datos"
        )
    
    return {
        "folio": folio,
        "datos": registro,
        "campos_disponibles": list(registro.keys()),
        "datos_etiqueta": {
            "ALMACEN_NOMBRE": registro.get("ALMACEN_NOMBRE"),
            "SUCURSAL_NOMBRE": registro.get("SUCURSAL_NOMBRE"),
            "CLAVE_ARTICULO": registro.get("CLAVE_ARTICULO"),
            "ARTICULO_NOMBRE": registro.get("ARTICULO_NOMBRE"),
            "ESDET_LOTE": registro.get("ESDET_LOTE"),
            "STOCK_LOTE": registro.get("STOCK_LOTE"),
            "ESDET_CADUCIDAD": registro.get("ESDET_CADUCIDAD"),
            "STOCK_CADUCIDAD": registro.get("STOCK_CADUCIDAD"),
            "ESDET_SERIE": registro.get("ESDET_SERIE"),
            "STOCK_ID": registro.get("STOCK_ID")
        }
    }


@app.post("/imprimir", response_model=PrintResponse)
async def imprimir_un_folio(request: FolioRequest):
    """
    Imprime una etiqueta RFID para un folio (10cm x 5cm)
    
    - **folio**: El folio en formato 'A00219-25'
    
    El proceso:
    1. Busca el folio en AMPAR_HIS_STOCK con JOINs a tablas relacionadas
    2. Actualiza STOCK_TEMPETIQUETA con el folio sin guión
    3. Imprime etiqueta con: Sucursal, Almacén, Clave, Artículo, Lote, Caducidad, Serie
    4. Incluye código de barras con el folio y QR con enlace al sistema
    """
    resultado = await imprimir_etiqueta(request.folio)
    
    if not resultado.success:
        raise HTTPException(status_code=400, detail=resultado.message)
    
    return resultado


@app.post("/imprimir-multiple", response_model=MultiplePrintResponse)
async def imprimir_multiples_folios(request: MultipleFoliosRequest):
    """
    Imprime múltiples etiquetas RFID (10cm x 5cm)
    
    - **folios**: Lista de folios en formato ['A00219-25', 'A00220-25', ...]
    
    Las etiquetas se imprimen secuencialmente con un delay entre cada una
    para evitar saturar la impresora.
    """
    resultados = []
    exitosos = 0
    fallidos = 0
    
    for i, folio in enumerate(request.folios):
        try:
            resultado = await imprimir_etiqueta(folio)
            resultados.append(resultado)
            
            if resultado.success:
                exitosos += 1
            else:
                fallidos += 1
            
            # Agregar delay entre impresiones (excepto en la última)
            if i < len(request.folios) - 1:
                await asyncio.sleep(PRINT_DELAY)
                
        except HTTPException as e:
            resultados.append(PrintResponse(
                success=False,
                message=str(e.detail),
                folio=folio,
                folio_sin_guion=folio.replace("-", "")
            ))
            fallidos += 1
    
    return MultiplePrintResponse(
        success=fallidos == 0,
        message=f"Procesados {len(request.folios)} folios: {exitosos} exitosos, {fallidos} fallidos",
        total_folios=len(request.folios),
        resultados=resultados
    )


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8090,
        log_level="info"
    )
