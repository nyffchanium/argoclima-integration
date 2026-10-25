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
Check **Temperature source**. The remote only sends the temperature by infrared while it is on and points at the device. If it's out of sight, covered or turned off, the device keeps its last value for about 7 minutes and then switches to its own sensor: **Temperature source** changes to **Device**. While the fan is stopped, that sensor measures the cold air at the heat exchanger and reads far too low, e.g. 16 °C in a 24 °C room. See [Using the remote's temperature sensor](features.md#using-the-remotes-temperature-sensor).
