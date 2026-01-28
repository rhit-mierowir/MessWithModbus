#!/usr/bin/env python3
from scapy.all import IP, TCP, send, sr1, RandShort
# This code is sourced from perplexity.ai and adjusted.

def tcp_handshake(src_ip, dst_ip, dport):
    """
    Perform a TCP 3-way handshake and return:
      ip, sport, dport, seq, ack
    where seq/ack are ready for the first data packet.
    """
    sport = RandShort()  # ephemeral client port

    ip = IP(src=src_ip, dst=dst_ip)

    # 1) SYN
    syn_seq = 100000  # arbitrary initial client seq
    syn = TCP(sport=sport, dport=dport, flags="S", seq=syn_seq)
    synack = sr1(ip/syn, timeout=2, verbose=0)
    if synack is None or not synack.haslayer(TCP):
        raise RuntimeError("No SYN/ACK from server")

    # 2) ACK
    srv_seq = synack[TCP].seq
    cli_seq = syn_seq + 1
    cli_ack = srv_seq + 1

    ack = TCP(
        sport=sport,
        dport=dport,
        flags="A",
        seq=cli_seq,
        ack=cli_ack
    )
    send(ip/ack, verbose=0)

    # Return info needed for data transfer
    return ip, sport, dport, cli_seq, cli_ack

def send_payloads(ip, sport, dport, init_seq, init_ack, payload_list):
    """
    Send a list of payloads over the established connection.
    payload_list: list of bytes/str to send as TCP segments.
    """
    seq = init_seq
    ack = init_ack

    for data in payload_list:
        if isinstance(data, str):
            data = data.encode()

        seg = TCP(
            sport=sport,
            dport=dport,
            flags="PA",  # PSH+ACK
            seq=seq,
            ack=ack
        )
        pkt = ip/seg/data
        send(pkt, verbose=0)

        seq += len(data)  # advance sequence by payload length

def main():
    # ----- CONFIG ----- #
    src_ip = "0.0.0.0"   # your VM's IP
    dst_ip = "127.0.0.1"   # server IP inside VM/lab
    dport  = 5020       # server port (e.g., Modbus/TCP)

    payloads = [
        b"\x00\x29\x00\x00\x00\x04\x01\x01\x01\x01",    # binary payload
    ]
    # ------------------ #

    ip, sport, dport, cli_seq, cli_ack = tcp_handshake(src_ip, dst_ip, dport)
    send_payloads(ip, sport, dport, cli_seq, cli_ack, payloads)

main()

