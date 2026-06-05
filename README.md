# 🌳 STP Root Claim — Secuestro del Root Bridge

## 🎯 Objetivo del Laboratorio

Demostrar cómo un atacante puede inyectar BPDUs STP con prioridad superior a la del switch legítimo, forzando una reconvergencia del árbol de expansión y convirtiéndose en el nuevo Root Bridge. Esto redirige el tráfico de la red a través del atacante, permitiendo un MitM a nivel de capa 2.

---

## 📋 Objetivo del Script

El script `STP_Root_Attack.py` construye y envía BPDUs de Configuración IEEE 802.1D estándar (sin tag) con prioridad efectiva `10` (prioridad `0` + VLAN_ID `10`), dirigidos al multicast STP `01:80:C2:00:00:00`. Al ser la prioridad más baja posible, todos los switches que procesen el BPDU elegirán a Kali como nuevo Root Bridge.

> **Nota sobre el puerto E0/3:** SW-1 tiene configurado `spanning-tree bpduguard enable` en E0/3. En el lab, para que el ataque STP sea observable, se debe deshabilitar temporalmente el BPDU Guard en ese puerto (ver sección de contra-medidas).

### Parámetros usados

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| `INTERFACE` | `ens4` | Interfaz física de Kali |
| `VLAN_ID` | `10` | VLAN objetivo; suma a la prioridad |
| `PRIORIDAD` | `0` | Prioridad base (mínima posible) |
| Prioridad efectiva | `10` | `0 + 10` vs `4106` de SW-1 → Kali gana |
| Loop infinito | `2 s` | Se mantiene como root enviando cada Hello Timer |

### Requisitos para utilizar la herramienta

```bash
# Dependencias
pip install scapy

# Deshabilitar BPDU Guard en SW-1 E0/3 para el lab:
SW-1(config-if)# no spanning-tree bpduguard enable

# Ejecución
sudo python3 STP_Root_Attack.py
```

---

## 🔧 Documentación del Funcionamiento del Script

### Flujo de ejecución

```
1. Obtener MAC de ens4 → usarla como Bridge ID y Root ID
2. Construir BPDU IEEE 802.1D (35 bytes):
     Protocol ID : 0x0000
     Version     : 0x00 (STP clásico)
     Type        : 0x00 (Configuration BPDU)
     Flags       : 0x01 (Topology Change)
     Root ID     : [prioridad 10][MAC Kali]
     Root Cost   : 0           ← somos la raíz
     Bridge ID   : [prioridad 10][MAC Kali]
     Port ID     : 0x8001
     Message Age : 0           ← generado en la raíz
     Max Age     : 20s
     Hello Time  : 2s
     Fwd Delay   : 15s
3. Encapsular en frame Ethernet:
     DA : 01:80:C2:00:00:00  (STP IEEE multicast)
     SA : MAC Kali
     LLC: DSAP=0x42 | SSAP=0x42 | Ctrl=0x03
4. Enviar cada 2 segundos por socket L2 persistente
5. Los switches comparan prioridades:
     SW-1 actual : Priority 4096 + 10 = 4106
     Kali        : Priority 0    + 10 = 10  ← GANA
6. Reconvergencia: ~30-50 segundos
```

### Comparación de Bridge IDs

```
Bridge ID actual de SW-1:
  Prioridad : 4096 (configurado)
  Sys-ID-Ext: 10   (VLAN 10)
  Efectiva  : 4106
  MAC       : aabb.cc00.0300

Bridge ID inyectado por Kali:
  Prioridad : 0    (mínima posible)
  Sys-ID-Ext: 10   (VLAN 10)
  Efectiva  : 10
  MAC       : <MAC de ens4>

Resultado: 10 < 4106 → Kali es elegida Root Bridge
```

### Por qué el frame es IEEE 802.1D sin tag

El puerto E0/3 de SW-1 está en modo **access VLAN 10**. Los BPDUs en puertos access se envían sin tag usando LLC `DSAP/SSAP = 0x42` (identificador STP IEEE). El script usa esta encapsulación para que el frame sea procesado por el switch como un BPDU STP válido.

---

## 🗺️ Documentación de la Red

### Topología

```
        [ R1 — IOU L3 ]
               |
           e0/0 (trunk)
               |
        [ SW-1 — IOL L2 ]  ← Root Bridge legítimo
          Priority: 4096     (prioridad efectiva: 4106)
          MAC: aabb.cc00.0300
         e0/1       e0/2       e0/3 ← access VLAN 10
          |           |           |
       [SW-3]       [SW-2]   [Kali]
                              ens4 → BPDU con priority 10
```

### Estado STP antes del ataque

```
SW-1# show spanning-tree vlan 10

VLAN0010
  Root ID  Priority 4106
           Address  aabb.cc00.0300
           This bridge is the root   ← SW-1 es raíz
```

### Estado STP esperado durante el ataque

```
SW-1# show spanning-tree vlan 10

VLAN0010
  Root ID  Priority 10
           Address  <MAC de Kali>    ← Kali es la nueva raíz
           Root port: Et0/3
```

---

## 📸 Capturas de Pantalla

> Insertar capturas en esta sección:

1. **`img/01_stp_antes.png`** — `show spanning-tree vlan 10` en SW-1 antes del ataque. `This bridge is the root`.
2. **`img/02_script_corriendo.png`** — Terminal Kali inyectando BPDUs. Contador de frames enviados.
3. **`img/03_stp_durante.png`** — `show spanning-tree vlan 10` en SW-1 durante el ataque. Root ID muestra la MAC de Kali con Priority 10.
4. **`img/04_topology_change.png`** — `show spanning-tree vlan 10 detail` mostrando `Topology changes` incrementando.
5. **`img/05_ping_timeout.png`** — Ping continuo desde VPC-1 a VPC-2 mostrando timeouts durante la reconvergencia.

---

## 🛡️ Contra-medidas

### BPDU Guard (ya configurado en SW-1 E0/3)

```
! Esta protección YA ESTÁ activa en la topología del lab:
SW-1(config)# interface Ethernet0/3
SW-1(config-if)# spanning-tree bpduguard enable
! → Si llega un BPDU por E0/3, el puerto pasa a err-disabled
!   de forma inmediata. El ataque STP queda bloqueado.

! Para reactivar el puerto tras una violación:
SW-1(config)# interface Ethernet0/3
SW-1(config-if)# shutdown
SW-1(config-if)# no shutdown

! Verificación
SW-1# show spanning-tree summary
SW-1# show interfaces Ethernet0/3 status
```

### Root Guard (en uplinks hacia switches de acceso)

```
! Evita que un switch downstream se convierta en raíz
SW-1(config)# interface Ethernet0/1
SW-1(config-if)# spanning-tree guard root
! (ya configurado en E0/1 → SW-3 según show run)

! Si llega un BPDU superior, el puerto pasa a root-inconsistent
! en lugar de aceptar el nuevo Root Bridge.

SW-1# show spanning-tree inconsistentports
```

### Portfast + BPDU Guard global

```
! Aplicar BPDU Guard a todos los puertos con PortFast
SW-1(config)# spanning-tree portfast bpduguard default
```

> **Resumen de protecciones STP:**
> - **BPDU Guard** → en puertos de acceso (usuarios); apaga el puerto si llega un BPDU.
> - **Root Guard** → en puertos de distribución; impide que un switch externo tome el rol de raíz.
> - **PortFast** → en puertos de usuario; evita el estado listening/learning innecesario.
