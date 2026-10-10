# Troubleshooting

## Reporting a problem

Please [open an issue](https://github.com/nyffchanium/argoclima-integration/issues/new/choose) and attach the diagnostics: **Settings → Devices & services → Argoclima → ⋮ → Download diagnostics**. IP addresses, device ids and names are removed from the file.

For debug logs, add this to `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.argoclima: debug
```

## Common problems

**The device can't be added or is unavailable although the IP is correct.**
Unplug the device for about a minute and try again.

**The connection drops every few seconds.**
This happens when Argo's server is overloaded: the device resets its WiFi connection when its requests to the server time out. The [dummy server](dummy-server.md) fixes this.

**The temperature is wrong while "Use Remote Temperature" is on.**
The remote only sends the temperature by infrared while it points at the device. If it's out of sight, covered or turned off, the device doesn't get new values and the temperature can be outdated. See [Using the remote's temperature sensor](features.md#using-the-remotes-temperature-sensor).
