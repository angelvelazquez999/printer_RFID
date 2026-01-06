import socket

ip = "192.168.1.150"
port = 9100

epc = "303400A1B2C3D4E5F6A7B8C9"

zgl = f"""
^XA
^PW820
^LL200
^LH0,0

~RFW,EPC,2,6,{epc}

^FO200,40
^BCN,40,Y,N,N
^FD7509552904468^FS

^FO200,110
^A0N,25,25
^FDEPC:{epc}^FS

^PQ1
^XZ
"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
s.sendall(zgl.encode("ascii"))
s.close()
