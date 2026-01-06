import socket

def print_with_pgl_forced_epc(ip, port, epc):
    
    pgl = f"""
~CREATE;TAG;EPC
~NORMAL;TAG;EPC
~ENCODING;HEX
~DATA;{epc}
~EXECUTE;SETEPC

~CREATE;BARCODE;BC1
~NORMAL;BARCODE;BC1
~BARPOS;200,40
~BARCHOICE;CODE128
~DATA;7509552904468
~EXECUTE;BC1

~CREATE;TEXT;TXT1
~NORMAL;TEXT;TXT1
~FONT;2
~TEXT;200,110;EPC: {epc}
~EXECUTE;TXT1

~PRINT;1,1
"""
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ip, port))
    s.sendall(pgl.encode("ascii"))
    s.close()
    
    print(f"Comando PGL enviado con EPC: {epc}")


print_with_pgl_forced_epc("192.168.1.150", 9100, "303400A1B2C3D4E5F6A7B8C9")

