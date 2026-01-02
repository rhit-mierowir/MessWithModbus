import scapy.all as s
from scapy.contrib import modbus
from dataclasses import dataclass

settings = {
    "ping_google":                      False,
    "example_IP_Hexdump":               False,
    "demonstrate_list_fields":          False,
    "Craft_Entire_IP_Packet_example":   False,
}

google_ipv6_addr = ("2001:4860:4860::8888", "2001:4860:4860::8844")

if settings["ping_google"]:
    print( 
            (
                s.sr1(s.IPv6(dst=google_ipv6_addr[0]) / s.ICMPv6EchoRequest(), verbose=0)
            ).summary()
        )

if settings["example_IP_Hexdump"]:
    a = s.IPv6()
    b = s.IP()
    print(s.hexdump(a))
    print(s.hexdump(b))

if settings["demonstrate_list_fields"]:
    print("="*15+" Ethernet "+"="*15)
    print(s.ls(s.Ether))
    print("="*15+" Internet Protocol (IP) "+"="*15)
    print(s.ls(s.IP))
    print("="*15+" TCP "+"="*15)
    print(s.ls(s.TCP))

if settings["Craft_Entire_IP_Packet_example"]:
    src_mac = 'f2:30:26:45:d1:f7'
    dst_mac = 'f2:ea:60:e5:b2:79'
    src_ip  = '52.194.106.139'
    dst_ip  = '131.17.59.243'
    src_port = 49556
    dst_port = 502
    a = s.Ether(src=src_mac,dst=dst_mac)/s.IP(src=src_ip, dst=dst_ip)/s.TCP(sport=src_port, dport=dst_port)
    a.display()



