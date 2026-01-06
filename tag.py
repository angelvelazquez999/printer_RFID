import socket

ip = "192.168.1.150"
port = 9100

data = """
<O>
<RW1,0,1234567890ABCDEF>
<FO50,50>
<TS30>
<T>TEST RFID
<P1>
"""

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((ip, port))
s.sendall(data.encode("ascii"))
s.close()
