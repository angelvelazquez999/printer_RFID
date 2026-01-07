import socket

ip = "192.168.1.150"
port = 9100

# ===== Datos dinámicos =====
barcode_value = "123456789"
rfid_text = "123456789ABCDEFG"          
label_text = "R1ID_DEV_2"             

# Convertir texto a HEX para EPC (12 bytes = 24 hex chars)
rfid_hex = rfid_text.encode("ascii").hex().upper()
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
^FD{barcode_value}^FS

^FO260,120
^A0N,30,30
^FD{label_text}^FS

^PQ1
^XZ
"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
s.sendall(zpl.encode("ascii"))
s.close()
