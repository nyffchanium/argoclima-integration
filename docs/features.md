# Features in detail

## Using the remote's temperature sensor

The device can use the temperature measured by the remote instead of its own sensor, which is often more accurate as the remote is usually closer to where you are.

The remote sends the temperature by **infrared**, the same way as its commands: only when it points at the device with a clear line of sight. It sends roughly every 6 minutes and whenever the displayed value changes.

1. Place the remote where it can "see" the device, e.g. on a shelf facing it.
2. Turn the remote on (grid lines and fan icon are visible).
3. Turn on **Use Remote Temperature** in Home Assistant. Enabling remote temperature mode on the remote itself (hold the fan button for 2 seconds; the user icon appears) may also be required.

Each transmission also includes the remote's own settings, which can overwrite changes made in Home Assistant. If that's a problem, keep the remote's settings in line with what you set in Home Assistant, or use the device's own sensor.

## Anti-mold

After cooling or dehumidifying, the inside of the device is wet. Turned off right away, the moisture stays inside and can cause mold and odors. With **Anti-mold** enabled, turning the device off in Home Assistant after cooling, dehumidifying or auto mode switches it to fan mode first and turns it off after the configured time.

Each device has these settings, all off or at their defaults until you change them:

| Entity                         | Default | Description                                                              |
| ------------------------------ | ------- | ------------------------------------------------------------------------ |
| Anti-mold                      | off     | Dry the device before turning it off                                     |
| Anti-mold after remote off     | off     | Also dry when the device was turned off with the remote or its timer; this turns it back on for drying |
| Anti-mold duration             | 15 min  | How long the fan keeps running                                           |
| Anti-mold fan speed            | medium  | Fan speed while drying                                                   |

**Anti-mold drying** shows whether the device is drying right now. Turning the device off again while drying turns it off immediately; any other change cancels drying. If Home Assistant restarts while drying, drying continues for the remaining time.

## Firmware updates

The device info shows the firmware of the device and, with the dummy server, of its WiFi module.

To be notified about new firmware, enable the **Firmware** (and **WiFi Firmware**) update entities of a device; they are disabled by default. Home Assistant then checks the latest versions on Argo's server once a day. The check doesn't send any credentials or device information.

Updates can't be installed from Home Assistant. Install them with the official Argo web app; if you use the [dummy server](dummy-server.md), disable the router rule while updating and enable it again afterwards. Argo publishes updates very rarely: as of October 2026, the latest versions are `01416` for the device and `00003` for the WiFi module.

## Delay timer

With **Active timer** set to **Delayed on/off**, the device turns itself on or off after the time set in **Delay timer duration** (10 minutes to almost 20 hours, in steps of 10 minutes; default 60 minutes). The duration is sent to the device when you activate the delay timer, or right away if it's already active.

## Device clock

The device has its own clock, used for its timers. The integration keeps it in sync automatically: once the device is first reachable, once a day, and after the device was unavailable, e.g. after a power cut.

To set a specific time or weekday, use the **Argoclima: Set time** action.

## Limitations

- The device only processes the most recent request; a running request is cancelled by a new one. Avoid using the official web app at the same time.
- Changes are re-sent until the device confirms them, up to three times.
- Write-only settings (time, weekday) can't be confirmed and are sent once.
- Eco, turbo and night mode can be combined on the remote but are exposed as mutually exclusive presets.
