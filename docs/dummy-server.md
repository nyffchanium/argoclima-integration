# Dummy server (advanced)

**Optional.** The integration works fine without it. It's worth setting up if your device often loses its connection, or if you want it to work without the manufacturer's cloud.

Argo devices are permanently connected to the manufacturer's cloud on the internet. When the cloud is overloaded, the device keeps dropping its WiFi connection, and if Argo ever shuts it down, the device can no longer be controlled over WiFi. The device also sends your Argo login and your WiFi password to the cloud, unencrypted.

The dummy server built into this integration takes the place of the cloud inside Home Assistant. Your router sends the device's traffic for the cloud to Home Assistant instead, so nothing leaves your network anymore:

- No more connection drops caused by the cloud, and no dependency on the internet.
- Your Argo login and WiFi password stay at home.
- The device reports its state on its own about every 12 seconds, and devices are found automatically.
- The official Argo web app no longer works while the dummy server is in use.

**You need a router that can redirect traffic** (called DNAT or "destination NAT"), e.g. UniFi, OPNsense, pfSense, FortiGate, MikroTik or OpenWrt. Most routers from internet providers, including the AVM FRITZ!Box, can't do this.

1. Go to **Settings → Devices & services → Add integration → Argoclima** and choose **Set up Argoclima Dummy Server**. Keep the suggested port `8239`.
2. Set up the redirect on your router. The **[router guide](dnat.md)** explains it step by step for each router.
3. Within a few minutes, your Argo devices show up under **Discovered** in **Settings → Devices & services**. Confirm them and give them a name. Devices you already added manually switch over automatically.

## Coming from the separate dummy server (Docker)

Earlier versions needed a separate dummy server running in Docker. It keeps working with this version: the integration then simply polls your devices as before. The Docker image is no longer updated, though. To switch to the built-in dummy server:

1. Set up the built-in dummy server as described above.
2. On your router, change the redirect so it points to Home Assistant and the dummy server port (`8239`) instead of the Docker container.
3. Once your devices show up under the dummy server in Home Assistant, stop and remove the Docker container.

## Security

- Never expose the dummy server port to the internet, and limit the router rules to your Argo devices.
- The dummy server only accepts a device report if the IP address it claims matches the address it connects from, or if it comes from the configured NAT gateway.
- The cloud credentials the device sends along are never stored and are removed from logs.

See also the [security policy](../SECURITY.md).
