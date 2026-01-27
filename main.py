"""
Microservicio para impresión de etiquetas RFID - Printronix AUTO ID T820
"""

import socket
import asyncio
from typing import List
from contextlib import asynccontextmanager

from firebird.driver import connect, driver_config
from fastapi import FastAPI, HTTPException, BackgroundTasks
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
    "database": "C:/laragon/www/amparv3/bd/AMPARJUL.FDB",  # Cambia esta ruta
    "user": "SYSDBA",
    "password": "masterkey",  # Cambia la contraseña
    "charset": "UTF8",
}

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
    Busca un folio en la tabla AMPAR_HIS_STOCK
    
    Args:
        folio: El folio a buscar (con guión, ej: 'A00219-25')
    
    Returns:
        dict con los datos del registro o None si no existe
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Buscar el folio en la base de datos
        cursor.execute(
            "SELECT * FROM AMPAR_HIS_STOCK WHERE STOCK_FOLIO = ?",
            (folio,)
        )
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

def generar_zpl(folio_sin_guion: str, folio_original: str, label_text: str = "") -> str:
    """
    Genera el código ZPL para la etiqueta RFID
    
    Args:
        folio_sin_guion: El folio sin guión para el RFID
        folio_original: El folio original con guión para el código de barras
        label_text: Texto adicional para la etiqueta (opcional)
    
    Returns:
        Código ZPL formateado
    """
    # Convertir texto a HEX para EPC (12 bytes = 24 hex chars)
    rfid_hex = folio_sin_guion.encode("ascii").hex().upper()
    rfid_hex = rfid_hex.ljust(24, "0")[:24]
    
    zpl = f"""
^XA
^PW820
^LL180
^LH0,0

^RS8,,100,1,E,,,6^FS

^RFW,H,2,16,1^FD{rfid_hex}^FS

^FO270,40
^BCN,60,Y,N,N
^FD{folio_original}^FS

^FO260,120
^A0N,30,30
^FD{label_text}^FS

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
        s.sendall(zpl.encode("ascii"))
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
    zpl = generar_zpl(folio_sin_guion, folio)
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

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes (en producción, especifica los dominios)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Endpoint de salud del servicio"""
    return {
        "status": "ok",
        "service": "RFID Label Printing API",
        "printer_ip": PRINTER_IP,
        "printer_port": PRINTER_PORT
    }


@app.get("/health")
async def health_check():
    """Verificación de salud del servicio"""
    return {"status": "healthy"}


@app.post("/imprimir", response_model=PrintResponse)
async def imprimir_un_folio(request: FolioRequest):
    """
    Imprime una etiqueta RFID para un folio
    
    - **folio**: El folio en formato 'A00219-25'
    
    El proceso:
    1. Busca el folio en AMPAR_HIS_STOCK
    2. Actualiza STOCK_TEMPETIQUETA con el folio sin guión
    3. Imprime la etiqueta con el código RFID y código de barras
    """
    resultado = await imprimir_etiqueta(request.folio)
    
    if not resultado.success:
        raise HTTPException(status_code=400, detail=resultado.message)
    
    return resultado


@app.post("/imprimir-multiple", response_model=MultiplePrintResponse)
async def imprimir_multiples_folios(request: MultipleFoliosRequest):
    """
    Imprime múltiples etiquetas RFID
    
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
