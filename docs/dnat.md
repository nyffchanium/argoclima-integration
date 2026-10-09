# Redirecting Argo traffic to the dummy server (DNAT)

The Argo devices have the address of Argo's cloud server (`31.14.128.210`, port `80`) built in; it can't be changed on the device. To use the [dummy server](../README.md#with-the-dummy-server-recommended), your router has to redirect this traffic to Home Assistant. This is called destination NAT (DNAT) or, on some routers, port forwarding.

> **Help wanted:** these guides are written from the vendors' documentation and haven't all been tested with Argo devices. If you use one of them, tell us whether it worked. If your router is missing or a guide is outdated, please [contribute](#contributing).

## Before you start

**Your router must support DNAT for traffic from your local network.** Port forwarding that only applies to traffic coming from the internet is not enough. Most consumer routers, including the AVM FRITZ!Box, can't do this.

**The Argo devices and Home Assistant must be in different subnets** (for example separate VLANs), so their traffic passes through the router.

<details>
<summary>Why different subnets?</summary>

If both are in the same subnet, the router only rewrites the device's request; Home Assistant then answers the device directly instead of through the router. The device expects the answer from `31.14.128.210`, ignores it, and the connection never completes. The usual fix, additional source NAT ("hairpin NAT"), makes all requests appear to come from the router. The dummy server rejects those, because it only accepts a device report from the IP address the device claims to have.

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

The examples use `192.168.30.90` and `192.168.30.91` for the Argo devices, `192.168.10.20` for Home Assistant and port `8080`.

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
| `claimed IP … did not match connection source …`        | Source NAT is applied, or device and Home Assistant share a subnet.      |
| `Failed to start Argoclima dummy server on port …`      | The port is already used by something else; choose another one.         |

## Contributing

Is your router missing, or is a guide wrong or outdated? Please help:

- **Edit this page** with the pencil icon on GitHub and open a pull request. Use the same structure and example addresses as the other guides.
- Or [open an issue](https://github.com/Gadund/argoclima-integration/issues/new/choose) with the steps or screenshots that worked for you, and the router model and firmware version.
- If a guide worked for you as is, a short note in an issue helps too.
