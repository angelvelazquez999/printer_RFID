import socket

def imprimir_pgl(ip, epc="9999", port=9100):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))

    pkt = bytearray()
    pkt.append(0x02)        

    pkt.extend(b"L\n")
    pkt.extend(b"1X110,10,0,3,2,2,ABC123\n")  
    pkt.extend(b"1B50,50,0,1,2,2,128,ABC123\n")  

    cmd = f'RFW,S,EPC,0,"{epc}"\n'
    pkt.extend(cmd.encode("ascii"))

    pkt.append(0x03)        

    s.sendall(pkt)
    s.close()
    print("Impreso + EPC escrito:", epc)

imprimir_pgl("192.168.1.150", "luis")
