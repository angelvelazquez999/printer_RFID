import socket
import time

def print_and_read_rfid(ip, port, epc):
    """
    Imprime etiqueta RFID y lee el EPC grabado
    """
    
    # ZGL con comandos de feedback RFID
    zgl = f"""^XA
^PW820
^LL200
^LH0,0

~SD30  
~JC^RFID_ERROR  

^RS8
^RFW,H,12^FD{epc}^FS

^RFR,H^FS

^FO200,40
^BCN,40,Y,N,N
^FD7509552904468^FS

^FO200,110
^A0N,25,25
^FDEPC: {epc}^FS

^PQ1
^XZ
"""

    try:
        # Crear socket con timeout
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)  # 10 segundos timeout
        
        print(f"Conectando a {ip}:{port}...")
        s.connect((ip, port))
        
        # Enviar comando ZGL
        print("Enviando job de impresión...")
        s.sendall(zgl.encode("ascii"))
        
        # Esperar un momento para que la impresora procese
        time.sleep(0.5)
        
        # Leer respuesta (puede venir en múltiples chunks)
        print("Esperando respuesta RFID...")
        response = b""
        s.settimeout(5)  # Timeout más corto para lectura
        
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
                print(f"Recibido chunk: {chunk}")
                
                # Si recibimos respuesta completa, salir
                if b"^RF" in response or b"~RFID" in response:
                    time.sleep(0.2)  # Esperar posible data adicional
                    try:
                        final = s.recv(4096)
                        if final:
                            response += final
                    except socket.timeout:
                        pass
                    break
                    
            except socket.timeout:
                print("Timeout - no hay más datos")
                break
        
        # Cerrar socket
        s.close()
        
        # Procesar respuesta
        if response:
            print("\n=== RESPUESTA COMPLETA ===")
            print(response.decode('ascii', errors='ignore'))
            print("=" * 50)
            
            # Parsear EPC de la respuesta
            epc_grabado = parse_rfid_response(response)
            return epc_grabado
        else:
            print("⚠️  No se recibió respuesta de la impresora")
            return None
            
    except socket.timeout:
        print("❌ Timeout - La impresora no respondió")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        try:
            s.close()
        except:
            pass


def parse_rfid_response(response):
    """
    Extrae el EPC de la respuesta de la impresora
    Formatos posibles:
    - ~RFID,EPC,3034257BF7194E4000000001
    - ^RF,EPC:3034257BF7194E4000000001
    - ^RFEPC3034257BF7194E4000000001
    """
    response_str = response.decode('ascii', errors='ignore')
    
    # Intentar diferentes patrones
    patterns = [
        "~RFID,EPC,",
        "^RF,EPC:",
        "^RFEPC",
        "EPC:",
    ]
    
    for pattern in patterns:
        if pattern in response_str:
            idx = response_str.find(pattern) + len(pattern)
            # Extraer siguiente segmento hexadecimal
            epc = ""
            for char in response_str[idx:]:
                if char in "0123456789ABCDEFabcdef":
                    epc += char
                elif epc:  # Si ya tenemos EPC y encontramos no-hex, terminar
                    break
            
            if len(epc) >= 24:  # EPC válido (96 bits = 24 hex chars)
                print(f"\n✅ EPC detectado: {epc}")
                return epc
    
    print("⚠️  No se pudo extraer EPC de la respuesta")
    return None


# Uso
if __name__ == "__main__":
    ip = "192.168.1.150"
    port = 9100
    epc = "303400A1B2C3D4E5F6A7B8C9"
    
    print("=" * 50)
    print("IMPRESIÓN RFID CON FEEDBACK")
    print("=" * 50)
    
    epc_grabado = print_and_read_rfid(ip, port, epc)
    
    if epc_grabado:
        print(f"\n✅ SUCCESS")
        print(f"   EPC enviado:  {epc}")
        print(f"   EPC grabado:  {epc_grabado}")
        print(f"   Coinciden:    {epc.upper() == epc_grabado.upper()}")
    else:
        print("\n❌ No se pudo verificar el EPC grabado")