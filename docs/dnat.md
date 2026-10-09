# Redirecting Argo traffic to the dummy server (DNAT)

The Argo devices have the address of Argo's cloud server (`31.14.128.210`, port `80`) built in; it can't be changed on the device. To use the [dummy server](../README.md#with-the-dummy-server-recommended), your router has to redirect this traffic to Home Assistant. This is called destination NAT (DNAT) or, on some routers, port forwarding.

> **Help wanted:** these guides are written from the vendors' documentation and haven't all been tested with Argo devices. If you use one of them, tell us whether it worked. If your router is missing or a guide is outdated, please [contribute](#contributing).

## Before you start

**Your router must support DNAT for traffic from your local network.** Port forwarding that only applies to traffic coming from the internet is not enough. Most consumer routers, including the AVM FRITZ!Box, can't do this.

**Check whether the Argo devices and Home Assistant are in the same subnet.** This decides which rules you need:

| Setup                                                   | Rules                                                                 |
| ------------------------------------------------------- | --------------------------------------------------------------------- |
| Different subnets (e.g. devices in their own VLAN)      | DNAT rule                                                             |
| Same subnet (e.g. both in `192.168.30.0/24`)            | DNAT rule, [hairpin NAT rule](#same-subnet-hairpin-nat) and the NAT gateway option |

<details>
<summary>Why does the same subnet need more?</summary>

The router only rewrites the device's request. Home Assistant sees the device in its own subnet and answers it directly instead of through the router. The device expects the answer from `31.14.128.210`, ignores it, and the connection never completes. A second rule (source NAT, "hairpin NAT") makes the router the sender, so the answer goes back through the router as well.

The dummy server normally only accepts a device report from the IP address the device claims to have. With hairpin NAT, all reports come from the router instead, so you tell the dummy server to trust it.

</details>

**Give your Argo devices static IP addresses** (DHCP reservations), so the rule can be limited to them.

## The rule

Every guide below creates the same rule:

| Setting                | Value                                                    |
| ---------------------- | -------------------------------------------------------- |
| Incoming interface     | The network/VLAN of your Argo devices                    |
| Protocol               | TCP                                                      |
| Source                 | Your Argo devices' IP addresses                          |
| Destination            | `31.14.128.210`, port `80`                               |
| Redirect to            | Your Home Assistant IP, dummy server port (default `8080`) |
| Source NAT/masquerade  | Off                                                      |

If your firewall blocks traffic between the two networks, also allow TCP from the Argo devices to Home Assistant on the dummy server port. Many routers create this rule for you.

The examples use `192.168.30.90` and `192.168.30.91` for the Argo devices, `192.168.10.20` for Home Assistant and port `8080`. In the same-subnet case, Home Assistant would be `192.168.30.20` and the router `192.168.30.1`.

## Router guides

### OPNsense

1. **Firewall → NAT → Destination NAT** (called **Port Forward** before 25.7) → **Add**.
2. Interface: the interface of the Argo network. Protocol: TCP.
3. Source: an alias with your Argo devices (**Firewall → Aliases**, type Host(s)).
4. Destination: Single host or network `31.14.128.210/32`, port range from/to `HTTP`.
5. Redirect target IP: `192.168.10.20`, redirect target port: `8080`.
6. Filter rule association: **Add associated filter rule** (or **Pass**).
7. Save and **Apply changes**.

### pfSense

1. **Firewall → NAT → Port Forward** → **Add**.
2. Interface: the interface of the Argo network. Protocol: TCP.
3. Source: your Argo devices (an alias under **Firewall → Aliases**).
4. Destination: Single host `31.14.128.210`, port range `HTTP`.
5. Redirect target IP: `192.168.10.20`, redirect target port: `8080`.
6. Filter rule association: **Add associated filter rule**.
7. Save and **Apply Changes**.

### Ubiquiti UniFi

Requires a UniFi gateway and a recent UniFi Network version with custom NAT rules. The menu location differs between versions.

1. **Settings → Policy Table → Create New Policy → NAT** (older versions: **Settings → Routing → NAT**).
2. Type: **Destination NAT**. Interface: the network of your Argo devices. Protocol: TCP.
3. Source: your Argo devices' IP addresses.
4. Destination: `31.14.128.210`, port `80`.
5. Translated IP address: `192.168.10.20`, translated port: `8080`.
6. Make sure no firewall policy blocks the Argo network from reaching Home Assistant on port `8080`.

### Fortinet FortiGate

1. **Policy & Objects → Virtual IPs → Create New → Virtual IP**:
   - Interface: the interface of the Argo network
   - External IP address: `31.14.128.210`
   - Mapped IP address: `192.168.10.20`
   - Port forwarding: enabled, protocol TCP, external port `80`, mapped port `8080`
2. **Policy & Objects → Firewall Policy → Create New**:
   - Incoming interface: the Argo network; outgoing interface: the Home Assistant network
   - Source: an address group with your Argo devices
   - Destination: the virtual IP from step 1
   - Service: HTTP, action: ACCEPT, **NAT: disabled**
3. Move the policy above any policy that sends this traffic to the internet.

### MikroTik RouterOS

```
/ip firewall address-list
add list=argo address=192.168.30.90
add list=argo address=192.168.30.91
/ip firewall nat
add chain=dstnat src-address-list=argo dst-address=31.14.128.210 protocol=tcp dst-port=80 \
    action=dst-nat to-addresses=192.168.10.20 to-ports=8080 comment="Argo dummy server"
```

Make sure no `srcnat`/masquerade rule applies to this traffic; a typical masquerade rule limited to `out-interface=WAN` doesn't.

### OpenWrt

Add to `/etc/config/firewall`, then run `service firewall restart`. Replace `lan` and `iot` with your zone names: `src` is the zone of the Argo devices, `dest` the zone of Home Assistant.

```
config redirect
	option name 'Argo dummy server'
	option target 'DNAT'
	option src 'iot'
	option src_ip '192.168.30.90'
	option src_dip '31.14.128.210'
	option src_dport '80'
	option dest 'lan'
	option dest_ip '192.168.10.20'
	option dest_port '8080'
	option proto 'tcp'
```

Add one section per device, or use an IP set.

### Linux (nftables)

```
table ip argo {
	chain prerouting {
		type nat hook prerouting priority dstnat;
		ip saddr { 192.168.30.90, 192.168.30.91 } ip daddr 31.14.128.210 tcp dport 80 dnat to 192.168.10.20:8080
	}
}
```

Your forward chain must allow the redirected traffic, and no masquerade rule may apply to it.

## Same subnet: hairpin NAT

Only needed if the Argo devices and Home Assistant are in the same subnet. Add this rule in addition to the DNAT rule above:

| Setting       | Value                                                   |
| ------------- | ------------------------------------------------------- |
| Interface     | The network of your Argo devices and Home Assistant     |
| Protocol      | TCP                                                     |
| Source        | Your Argo devices' IP addresses                         |
| Destination   | Your Home Assistant IP, dummy server port               |
| Translation   | Source NAT to the router's address (masquerade)         |

Limit the rule to your Argo devices: the dummy server trusts every report that comes from the router.

Then, in Home Assistant, open the dummy server's options (**Settings → Devices & services → Argoclima → Argoclima Dummy Server → Configure**) and enter the router's IP address in this subnet (e.g. `192.168.30.1`) as **NAT gateway**.

**OPNsense:** **Firewall → NAT → Source NAT** (called **Outbound** before 25.7). Set the mode to **Hybrid**, add a rule with interface: the Argo network, protocol TCP, source: your Argo alias, destination `192.168.30.20/32` port `8080`, translation: **Interface address**.

**pfSense:** **Firewall → NAT → Outbound**. Set the mode to **Hybrid Outbound NAT**, add a mapping with interface: the Argo network, protocol TCP, source: your Argo alias, destination `192.168.30.20/32` port `8080`, translation: **Interface Address**.

**Ubiquiti UniFi:** create a second NAT policy of type **Source NAT** (or **Masquerade**) with source: your Argo devices, destination `192.168.30.20` port `8080`, translated IP: the gateway's address in this network.

**Fortinet FortiGate:** use the Argo network as both incoming and outgoing interface in the firewall policy and **enable NAT** (outgoing interface address).

**MikroTik RouterOS:**

```
/ip firewall nat
add chain=srcnat src-address-list=argo dst-address=192.168.30.20 protocol=tcp dst-port=8080 \
    action=masquerade comment="Argo dummy server hairpin"
```

**OpenWrt:**

```
config nat
	option name 'Argo dummy server hairpin'
	option src 'lan'
	option src_ip '192.168.30.90'
	option dest_ip '192.168.30.20'
	option dest_port '8080'
	option proto 'tcp'
	option target 'MASQUERADE'
```

**Linux (nftables):**

```
table ip argo {
	chain postrouting {
		type nat hook postrouting priority srcnat;
		ip saddr { 192.168.30.90, 192.168.30.91 } ip daddr 192.168.30.20 tcp dport 8080 masquerade
	}
}
```

## Checking that it works

Enable info logging in `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  logs:
    custom_components.argoclima: info
```

Within a few minutes, the log should show `Argoclima UI_FLG push received for CPU_ID …` for each device, and the devices appear as discovered devices.

| Log message                                             | Cause                                                                    |
| ------------------------------------------------------- | ------------------------------------------------------------------------ |
| Nothing at all                                          | The rule doesn't match or a firewall blocks the traffic.                 |
| `claimed IP … did not match connection source …`        | The traffic is source-NATed. If that's your hairpin rule, set the NAT gateway option to the address shown as connection source. |
| `Failed to start Argoclima dummy server on port …`      | The port is already used by something else; choose another one.         |

## Contributing

Is your router missing, or is a guide wrong or outdated? Please help:

- **Edit this page** with the pencil icon on GitHub and open a pull request. Use the same structure and example addresses as the other guides.
- Or [open an issue](https://github.com/Gadund/argoclima-integration/issues/new/choose) with the steps or screenshots that worked for you, and the router model and firmware version.
- If a guide worked for you as is, a short note in an issue helps too.
