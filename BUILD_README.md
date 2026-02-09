# RFID Label Printing API - Compilación a EXE

## Compilar a ejecutable

### Opción 1: Usar el script automático
```bash
build.bat
```

### Opción 2: Manualmente
```bash
# Instalar PyInstaller
poetry add pyinstaller --group dev

# Compilar
poetry run pyinstaller rfid-printer.spec --clean
```

## Ejecutar el .exe

El ejecutable se generará en `dist/rfid-printer-api.exe`

### Uso básico:
```bash
rfid-printer-api.exe
```
Por defecto inicia en puerto **8090**

### Con puerto personalizado:
```bash
rfid-printer-api.exe 9000
```

## Configuración

Antes de distribuir el ejecutable, **edita `main.py`** y ajusta:

1. **IP de la impresora** (línea 21):
   ```python
   PRINTER_IP = "192.168.1.150"
   ```

2. **Base de datos Firebird** (líneas 25-31):
   ```python
   FIREBIRD_CONFIG = {
       "host": "localhost",
       "database": "C:/ruta/a/tu/base.FDB",
       "user": "SYSDBA",
       "password": "masterkey",
       "charset": "UTF8",
   }
   ```

3. **URL del QR** (línea 34):
   ```python
   QR_BASE_URL = "http://tu-servidor.com/..."
   ```

## Distribución

Una vez compilado, puedes copiar **solo** el archivo `rfid-printer-api.exe` a cualquier servidor Windows que tenga:
- Acceso a la impresora RFID
- Acceso a la base de datos Firebird

## Endpoints disponibles

- **GET** `/` - Estado del servicio
- **GET** `/health` - Health check
- **GET** `/consultar/{folio}` - Consultar datos de un folio
- **POST** `/imprimir` - Imprimir una etiqueta
- **POST** `/imprimir-multiple` - Imprimir múltiples etiquetas

Documentación completa: `http://localhost:8090/docs`

## Notas

- El ejecutable es **portable** - no requiere instalación
- Incluye todas las dependencias (FastAPI, Uvicorn, Firebird driver, etc.)
- Tamaño aproximado: 40-60 MB
- Compatible con Windows 10/11 y Windows Server
