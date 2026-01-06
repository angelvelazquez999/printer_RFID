import socket

def texto_a_hex(texto):
    """Convierte texto ASCII a hexadecimal"""
    return texto.encode('ascii').hex().upper()

ip = "192.168.1.150"
port = 9100

# Tus datos
epc_data = "303400A1B2C3D4E5F6A7B8C9"
user_texto = "LOTE2024-001"  # Texto que quieres en USER
user_data = texto_a_hex(user_texto)  # Convertido a hex

zpl = f"""
^XA
^PW820
^LL200
^LH0,0

^RS8,,,2,0                 
^RFW,E,3,{epc_data}
^RFW,U,3,{user_data}

^FO270,40
^BCN,60,Y,N,N
^FD{epc_data}^FS

^FO270,120
^A0N,30,30
^FDUSER:{user_texto}^FS

^PQ1
^XZ
"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
s.sendall(zpl.encode("ascii"))
s.close()

print(f"✓ Etiqueta enviada:")
print(f"  EPC: {epc_data}")
print(f"  USER (texto): {user_texto}")
print(f"  USER (hex): {user_data}")