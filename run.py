"""
Script de entrada para el ejecutable del microservicio RFID
"""
import uvicorn
import sys
import os

# Fijar el puerto por defecto
DEFAULT_PORT = 8090
DEFAULT_HOST = "0.0.0.0"

if __name__ == "__main__":
    # Obtener puerto de argumentos o usar default
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Puerto inválido, usando {DEFAULT_PORT}")
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     RFID Label Printing API - Printronix T820            ║
║═══════════════════════════════════════════════════════════║
║  Servidor escuchando en: http://{DEFAULT_HOST}:{port}              ║
║  Documentación: http://localhost:{port}/docs              ║
║═══════════════════════════════════════════════════════════║
║  Presiona CTRL+C para detener el servidor                ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Importar la app de main
    from main import app
    
    # Ejecutar servidor
    uvicorn.run(
        app,
        host=DEFAULT_HOST,
        port=port,
        log_level="info"
    )
