# Redirecting Argo traffic to the dummy server (DNAT)

**In short:** your Argo device keeps trying to reach Argo's server on the internet. You tell your router: "when the Argo device wants to reach Argo's server, send it to Home Assistant instead." That's all this guide is about. It's a one-time setup on the router; nothing needs to change on the device.

The Argo devices have the addresses of Argo's cloud servers built in: `31.14.128.210` and, as a fallback, `95.254.67.59`, both on port `80`. They can't be changed on the device. To use the [dummy server](dummy-server.md), your router has to redirect this traffic to Home Assistant. This is called destination NAT (DNAT) or, on some routers, port forwarding.

Redirect both addresses: a device that can't reach the first one switches to the fallback.

> **Help wanted:** the UniFi guide has been tested with a UniFi Dream Machine. The other guides are written from the vendors' documentation. If you use one of them, tell us whether it worked. If your router is missing or a guide is outdated, please [contribute](#contributing).

## Before you start

**Your router must support DNAT for traffic from your local network.** Port forwarding that only applies to traffic coming from the internet is not enough. Most consumer routers, including the AVM FRITZ!Box, can't do this.

**Check whether the Argo devices and Home Assistant are in the same subnet.** This decides which rules you need:

| Setup                                                   | Rules                                                                 |
| ------------------------------------------------------- | --------------------------------------------------------------------- |
| Different subnets (e.g. devices in their own VLAN)      | DNAT rule                                                             |
| Same subnet (e.g. both in the same VLAN)                | DNAT rule, [hairpin NAT rule](#same-subnet-hairpin-nat) and the NAT gateway option |

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
| Destination            | `31.14.128.210` and `95.254.67.59`, port `80`            |
| Redirect to            | Your Home Assistant IP, dummy server port (default `8239`) |
| Source NAT/masquerade  | Off                                                      |

**Firewall:** allow TCP from the Argo devices to Home Assistant on the dummy server port. Redirected traffic passes the router's firewall like routed traffic, even if the devices and Home Assistant are in the same subnet. Some routers create this rule for you; UniFi doesn't.

Replace the placeholders in the examples:

| Placeholder            | Meaning                                                        |
| ---------------------- | -------------------------------------------------------------- |
| `<home-assistant-ip>`  | IP address of Home Assistant                                   |
| `<argo-device-ip>`     | IP address of an Argo device (add one entry per device)        |
| `<router-ip>`          | IP address of your router in the Argo devices' network         |
| `8239`                 | Dummy server port, if you changed it                           |

## Router guides

### OPNsense

1. **Firewall → NAT → Destination NAT** (called **Port Forward** before 25.7) → **Add**.
2. Interface: the interface of the Argo network. Protocol: TCP.
3. Source: an alias with your Argo devices (**Firewall → Aliases**, type Host(s)).
4. Destination: an alias with `31.14.128.210` and `95.254.67.59`, port range from/to `HTTP`.
5. Redirect target IP: `<home-assistant-ip>`, redirect target port: `8239`.
6. Filter rule association: **Add associated filter rule** (or **Pass**).
7. Save and **Apply changes**.

### pfSense

1. **Firewall → NAT → Port Forward** → **Add**.
2. Interface: the interface of the Argo network. Protocol: TCP.
3. Source: your Argo devices (an alias under **Firewall → Aliases**).
4. Destination: an alias with `31.14.128.210` and `95.254.67.59`, port range `HTTP`.
5. Redirect target IP: `<home-assistant-ip>`, redirect target port: `8239`.
6. Filter rule association: **Add associated filter rule**.
7. Save and **Apply Changes**.

### Ubiquiti UniFi

Tested with a UniFi Dream Machine. Requires UniFi Network 9.3 or newer.

1. Optional, but makes the rules easier to read: create objects for your Argo devices, for the two Argo server addresses and for port `80`.
2. **Settings → Policy Engine → NAT → Create New**:
   - Type: **Destination NAT**
   - Interface: the network of your Argo devices
   - Protocol: TCP
   - Source: your Argo devices
   - Destination: `31.14.128.210` and `95.254.67.59`, port `80`
   - Translated IP address: `<home-assistant-ip>`, translated port: `8239`
3. **Settings → Policy Engine → Firewall**: create an **Allow** policy from your Argo devices to `<home-assistant-ip>`, TCP port `8239`. UniFi's firewall drops the redirected traffic otherwise, also within the same network.
4. Same subnet only: add the [hairpin NAT rule](#same-subnet-hairpin-nat).

UniFi's traffic and flow views keep listing the device's connections to Argo's servers, partly with "Internet" as destination. They show the original destination before the redirect. To confirm nothing leaves your network, capture on the WAN interface via SSH; it should show no packets:

```
timeout 60 tcpdump -ni eth9 host 31.14.128.210 or host 95.254.67.59
```

Replace `eth9` with your WAN interface (`ip route | grep default`).

### Fortinet FortiGate

1. **Policy & Objects → Virtual IPs → Create New → Virtual IP**:
   - Interface: the interface of the Argo network
   - External IP address: `31.14.128.210` (create a second virtual IP for `95.254.67.59` and add both to a VIP group)
   - Mapped IP address: `<home-assistant-ip>`
   - Port forwarding: enabled, protocol TCP, external port `80`, mapped port `8239`
2. **Policy & Objects → Firewall Policy → Create New**:
   - Incoming interface: the Argo network; outgoing interface: the Home Assistant network
   - Source: an address group with your Argo devices
   - Destination: the virtual IP (group) from step 1
   - Service: HTTP, action: ACCEPT, **NAT: disabled**
3. Move the policy above any policy that sends this traffic to the internet.

### MikroTik RouterOS

```
/ip firewall address-list
add list=argo address=<argo-device-ip-1>
add list=argo address=<argo-device-ip-2>
add list=argo-servers address=31.14.128.210
add list=argo-servers address=95.254.67.59
/ip firewall nat
add chain=dstnat src-address-list=argo dst-address-list=argo-servers protocol=tcp dst-port=80 \
    action=dst-nat to-addresses=<home-assistant-ip> to-ports=8239 comment="Argo dummy server"
```

Make sure no `srcnat`/masquerade rule applies to this traffic; a typical masquerade rule limited to `out-interface=WAN` doesn't.

### OpenWrt

Add to `/etc/config/firewall`, then run `service firewall restart`. Replace `lan` and `iot` with your zone names: `src` is the zone of the Argo devices, `dest` the zone of Home Assistant.

```
config redirect
	option name 'Argo dummy server'
	option target 'DNAT'
	option src 'iot'
	option src_ip '<argo-device-ip>'
	option src_dip '31.14.128.210'
	option src_dport '80'
	option dest 'lan'
	option dest_ip '<home-assistant-ip>'
	option dest_port '8239'
	option proto 'tcp'
```

Add one section per device and server address, or use IP sets.

### Linux (nftables)

```
table ip argo {
	chain prerouting {
		type nat hook prerouting priority dstnat;
		ip saddr { <argo-device-ip-1>, <argo-device-ip-2> } ip daddr { 31.14.128.210, 95.254.67.59 } tcp dport 80 dnat to <home-assistant-ip>:8239
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

Then, in Home Assistant, open the dummy server's options (**Settings → Devices & services → Argoclima → Argoclima Dummy Server → Configure**) and enter the router's IP address in this subnet (`<router-ip>`) as **NAT gateway**.

**OPNsense:** **Firewall → NAT → Source NAT** (called **Outbound** before 25.7). Set the mode to **Hybrid**, add a rule with interface: the Argo network, protocol TCP, source: your Argo alias, destination `<home-assistant-ip>/32` port `8239`, translation: **Interface address**.

**pfSense:** **Firewall → NAT → Outbound**. Set the mode to **Hybrid Outbound NAT**, add a mapping with interface: the Argo network, protocol TCP, source: your Argo alias, destination `<home-assistant-ip>/32` port `8239`, translation: **Interface Address**.

**Ubiquiti UniFi:** **Settings → Policy Engine → NAT → Create New**, type **Masquerade**, interface: the network of your Argo devices, protocol TCP, source: your Argo devices, destination `<home-assistant-ip>` port `8239`. The firewall policy from the guide above is required here as well.

**Fortinet FortiGate:** use the Argo network as both incoming and outgoing interface in the firewall policy and **enable NAT** (outgoing interface address).

**MikroTik RouterOS:**

```
/ip firewall nat
add chain=srcnat src-address-list=argo dst-address=<home-assistant-ip> protocol=tcp dst-port=8239 \
    action=masquerade comment="Argo dummy server hairpin"
```

**OpenWrt:**

```
config nat
	option name 'Argo dummy server hairpin'
	option src 'lan'
	option src_ip '<argo-device-ip>'
	option dest_ip '<home-assistant-ip>'
	option dest_port '8239'
	option proto 'tcp'
	option target 'MASQUERADE'
```

**Linux (nftables):**

```
table ip argo {
	chain postrouting {
		type nat hook postrouting priority srcnat;
		ip saddr { <argo-device-ip-1>, <argo-device-ip-2> } ip daddr <home-assistant-ip> tcp dport 8239 masquerade
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
| Nothing at all                                          | The rule doesn't match, the firewall drops the redirected traffic, or (same subnet) the hairpin rule is missing. |
| `claimed IP … did not match connection source …`        | The traffic is source-NATed. If that's your hairpin rule, set the NAT gateway option to the address shown as connection source. |
| `Failed to start Argoclima dummy server on port …`      | The port is already used by something else; choose another one.         |

### Checking the rules on the router

On Linux-based routers such as UniFi gateways or OpenWrt, the packet counters show where the traffic stops. On a UniFi gateway, via SSH:

```
iptables -t nat -L UBIOS_PREROUTING_USER_HOOK -n -v
iptables -t nat -L UBIOS_POSTROUTING_USER_HOOK -n -v
```

| Counters                                    | Meaning                                                              |
| ------------------------------------------- | -------------------------------------------------------------------- |
| DNAT stays at 0                             | The DNAT rule doesn't match: check interface, source and destination. |
| DNAT rises, masquerade stays at 0           | The firewall drops the redirected traffic: add the allow rule.       |
| Both rise, still nothing in the log         | Check the NAT gateway option in Home Assistant.                      |

## Contributing

Is your router missing, or is a guide wrong or outdated? Please help:

- **Edit this page** with the pencil icon on GitHub and open a pull request. Use the same structure and example addresses as the other guides.
- Or [open an issue](https://github.com/nyffchanium/argoclima-integration/issues/new/choose) with the steps or screenshots that worked for you, and the router model and firmware version.
- If a guide worked for you as is, a short note in an issue helps too.
