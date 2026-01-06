import socket

ip = "192.168.1.150"
port = 9100

# EPC de ejemplo: 11223344556677889900AABB
EPC = "11223344556677889900AABB"

# PC para 12 palabras (24 bytes EPC) = 3000
PC = "3000"

FULL = PC + EPC  # PC + EPC

zpl = f"""
^XA
^PW820
^LL180
^LH0,0

^RS8,2,4,30,3,2,0,0

^RFU,L,0,1,00000000           ; Unlock EPC
^RFW,H,1,13,300011223344556677889900AABB

^FO270,40
^BCN,60,Y,N,N
^FD11223344556677889900AABB^FS

^FO260,120
^A0N,30,30
^FDRFID OK^FS

^PQ1
^XZ
"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
s.sendall(zpl.encode("ascii"))
s.close()
