from scapy.all import rdpcap, sendp
import time
PCAP_FILE_ON = "pump_on.pcapng"     # path to your pcap, pcapng
PCAP_FILE_OFF = "pump_off.pcapng"   # path to a second pcap, pcapng
IFACE = "lo"                      # change to your interface name  
INTERVAL = 5                        # seconds between replays  
 
def main():
    # Load all packets from pcap
    on_packets = rdpcap(PCAP_FILE_ON)     # returns a PacketList
    off_packets = rdpcap(PCAP_FILE_OFF)
    print(f"Loaded {len(on_packets)} packets from {PCAP_FILE_ON}")
    print(f"Loaded {len(off_packets)} packets from {PCAP_FILE_OFF}")

    while True:
        print("Replaying pcap...")
        # sendp sends at layer 2
        sendp(on_packets, iface=IFACE, inter=0, verbose=True)
        time.sleep(INTERVAL)
        sendp(off_packets, iface=IFACE, inter=0, verbose=True)
        time.sleep(INTERVAL)

main()
