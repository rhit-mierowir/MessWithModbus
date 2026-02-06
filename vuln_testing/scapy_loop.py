from scapy.all import rdpcap, sendp
PCAP_FILE = "./<filename>"      # path to your pcap, pcapng
IFACE = "eth0"                  # change to your interface name
INTERVAL = 0.1                    # seconds between *packets*

def main():
	packets = rdpcap(PCAP_FILE)
	print(f"Loaded {len(packets)} packets from {PCAP_FILE}")

	# loop=1 means “send in loop indefinitely”
	sendp(packets, iface=IFACE, loop=1, inter=INTERVAL, verbose=1)

main()
