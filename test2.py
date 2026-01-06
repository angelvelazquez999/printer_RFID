import socket

def imprimir_pgl(ip, port=9100):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))

        data = bytearray()
        data.append(0x02)                 # STX
        data.extend(b'L\n')               # Begin label
        data.extend(b'B50,50,0,1,2,2,128,"ABC123"\n')
        data.append(0x03)                 # ETX

        s.sendall(data)
        s.close()
        print("Etiqueta enviada correctamente.")
    except Exception as e:
        print("Error al imprimir:", e)


imprimir_pgl("192.168.1.150")
