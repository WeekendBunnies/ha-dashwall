# Dashwall for Home Assistant

A Home Assistant integration for Dashwall wall tablets. Wake the screen, reload
the dashboard and follow the tablet's battery and connection, all over your own
network: local push, no cloud, no MQTT broker.

## Installation

[![Open your Home Assistant instance and open this repository inside HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=WeekendBunnies&repository=ha-dashwall&category=integration)

**HACS:** the button opens this repository in HACS (it uses [My Home Assistant](https://www.home-assistant.io/integrations/my/), which is
on by default). Or by hand: HACS > three dots > Custom repositories > add
`https://github.com/WeekendBunnies/ha-dashwall` as type *Integration*, install
**Dashwall**, then restart Home Assistant.

**By hand:** copy `custom_components/dashwall` into your Home Assistant
`config/custom_components/` folder and restart.

## Setup

Tablets on your network are found automatically: Settings > Devices & services
shows them as discovered. Select **Add**, then **Submit**.

Pairing completes once the tablet's dashboard is logged in to this Home
Assistant, so only someone who can log in to Home Assistant can pair a tablet.
If the tablet shows the login page, log in there within five minutes.

To add a tablet by hand, use the button or **Add integration > Dashwall**,
and enter its address (port 2971).

[![Open your Home Assistant instance and start setting up Dashwall.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=dashwall)

## Entities

| Entity | Type |
|---|---|
| Wake screen, Reload dashboard | buttons |
| Connected | whether Home Assistant can reach the tablet |
| Screen, Dashboard connected | binary sensors |
| Battery, Battery state, Battery temperature, Battery power, Charging, Remaining charge time | battery |
| Kiosk mode | hides Home Assistant's top bar and side menu on the tablet only; other browsers show the dashboard as usual |
| Page zoom, Dashboard URL, Keep CPU awake, Wi-Fi full power | settings you can change from Home Assistant |
| Last seen, Dashboard state, Charger connected, Charger type, Battery health, Dashboard reloads, Last reload reason, Last event, App version | diagnostics |

The battery entities use the same values as the Home Assistant Companion app's
battery sensors, so existing cards and automations can switch over directly.

## Example: wake the screen on motion

```yaml
automation:
  - alias: Wake the wall tablet on motion
    triggers:
      - trigger: state
        entity_id: binary_sensor.hallway_motion
        to: "on"
    actions:
      - action: button.press
        target:
          entity_id: button.living_room_tablet_wake_screen
```

## Security

Every request to the tablet is signed (HMAC-SHA256) with a key that is agreed
during pairing through Home Assistant's own login. Each signature is valid for
a few minutes and only once. Nothing leaves your local network.

## Requirements

Home Assistant 2025.3 or later. The integration's icon shows from Home
Assistant 2026.3.

## License

MIT
