import socket

def enviar_etiqueta_pgl(ip, puerto=9100):
    """
    Envía una etiqueta PGL a la impresora Printronix T820
    
    Args:
        ip: Dirección IP de la impresora
        puerto: Puerto de conexión (por defecto 9100)
    """
    
    # Comandos PGL para etiqueta de 104mm x 23mm
    # Sintaxis PGL correcta para Printronix
    pgl_commands = (
        "\x1B"  # ESC - Inicio de comando
        "A"     # Comando A para iniciar trabajo
        "\x1B"
        "R000,020,0830,0184"  # Rectángulo: X,Y,Ancho,Alto
        "\x1B"
        "T5,0050,0050,1,1,1,0,N;Producto XYZ"
        "\x1B"
        "T5,0050,0100,1,1,1,0,N;Codigo: 12345"
        "\x1B"
        "T5,0050,0150,1,1,1,0,N;Lote: A001"
        "\x1B"
        "XB"    # Imprimir etiqueta
        "\r\n"
    )
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        
        print(f"Conectando a {ip}:{puerto}...")
        sock.connect((ip, puerto))
        
        print("Enviando etiqueta...")
        sock.sendall(pgl_commands.encode('cp850'))
        
        print("✓ Etiqueta enviada exitosamente")
        
    except socket.timeout:
        print("✗ Error: Tiempo de espera agotado")
    except ConnectionRefusedError:
        print("✗ Error: Conexión rechazada. Verifica IP y puerto")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        sock.close()


def enviar_etiqueta_simple(ip, puerto=9100):
    """
    Versión simplificada - solo texto sin rectángulo
    """
    pgl_commands = (
        "\x1BA"  # ESC A - Iniciar trabajo
        "\x1BT5,0100,0050,1,1,1,0,N;PRUEBA LINEA 1"
        "\x1BT5,0100,0100,1,1,1,0,N;PRUEBA LINEA 2"
        "\x1BT5,0100,0150,1,1,1,0,N;PRUEBA LINEA 3"
        "\x1BXB"  # ESC XB - Imprimir
        "\r\n"
    )
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip, puerto))
        print("Enviando etiqueta simple...")
        sock.sendall(pgl_commands.encode('cp850'))
        print("✓ Enviado")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        sock.close()


def enviar_con_codigo_barras(ip, texto1, texto2, codigo_barras, puerto=9100):
    """
    Etiqueta con código de barras
    """
    pgl_commands = (
        "\x1BA"  # Iniciar
        f"\x1BT5,0050,0040,1,1,1,0,B;{texto1}"
        f"\x1BT5,0050,0090,1,1,1,0,N;{texto2}"
        f"\x1BB2,0050,0140,1,2,3,50,0,0;{codigo_barras}"  # Código de barras
        "\x1BXB"
        "\r\n"
    )
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((ip, puerto))
        print("Enviando etiqueta con código de barras...")
        sock.sendall(pgl_commands.encode('cp850'))
        print("✓ Enviado")
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    PRINTER_IP = "192.168.1.150"
    
    # Prueba 1: Etiqueta simple (recomendado probar primero)
    print("\n=== PRUEBA 1: Etiqueta Simple ===")
    enviar_etiqueta_simple(PRINTER_IP)
    
    # Descomentar para probar otras versiones:
    # print("\n=== PRUEBA 2: Etiqueta Completa ===")
    # enviar_etiqueta_pgl(PRINTER_IP)
    
    # print("\n=== PRUEBA 3: Con Código de Barras ===")
    # enviar_con_codigo_barras(PRINTER_IP, "Mi Producto", "Lote: X123", "123456789012")