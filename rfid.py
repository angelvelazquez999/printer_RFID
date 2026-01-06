import socket

ip = "192.168.1.150"
port = 9100

zpl = """
^XA
^PW820
^LL180
^LH0,0

^RS8,2,4,30,3,2,0,0      

^RFW,H,0,12,123456789ABCDEF012345678  

^FO270,40
^BCN,60,Y,N,N
^FD123456789^FS

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
