import socket

ip = "192.168.1.150"
port = 9100

data = (
    "^XA\r\n"
    "^CF0,30\r\n"
    "^FO20,20^FDHELLO ZPL TEST^FS\r\n"
    "^XZ\r\n"
)

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((ip, port))
    s.sendall(data.encode("ascii"))
    s.close()
    print("Enviado: ZPL simple")
except Exception as e:
    print("Error:", e)
