# SIP Indoor Station Integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=arturzx&repository=sip-indoor-station-integration&category=integration)

Home Assistant integration for the [SIP Indoor Station add-on](https://github.com/arturzx/hass-addons/tree/master/sip_indoor_station).

## Requirements

- Add-on installed and running in Home Assistant.

## Entities

The integration creates door station device, with these entities:

- `binary_sensor`: Registered
- `binary_sensor`: Ringing
- `binary_sensor`: In call
- `sensor`: Call state
- `button`: Answer
- `button`: Reject
- `button`: Hang up
- `button`: Open door
- `button`: Reboot

Possible call state values:

- `idle`: no call is active.
- `ringing`: an incoming call is waiting for answer or rejection.
- `answered`: the call has been answered and is active.
- `rejected`: the incoming call was rejected by user.
- `cancelled`: the caller cancelled the call before it was answered or timeout occurred.
- `ended`: the active call ended normally (by user or caller).
- `failed`: the call failed.

The call-state sensor also includes useful attributes such as `call_id`, `remote_ip`, registration source, selected audio codec, and last event metadata.

## Installation

### HACS (Recommended)

Open this repository in HACS:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=arturzx&repository=sip-indoor-station-integration&category=integration)

Or add it manually in HACS:

1. Open HACS.
2. Open the three-dot menu and select **Custom repositories**.
3. Add `https://github.com/arturzx/sip-indoor-station-integration`.
4. Select category `Integration`.
5. Install `SIP Indoor Station`.
6. Restart Home Assistant.

Then add the integration from:

```text
Settings -> Devices & services -> Add integration -> SIP Indoor Station
```

### Manual

Copy `custom_components/sip_indoor_station` into your Home Assistant `custom_components` directory and restart Home Assistant.

Then add the integration from:

```text
Settings -> Devices & services -> Add integration -> SIP Indoor Station
```

## Configuration

Device name defaults to:

```text
Door station
```

Default add-on slug:

```text
c1b42bc7_sip_indoor_station
```

By default, the integration proxies to:

```text
http://c1b42bc7-sip-indoor-station:8080
```

If your add-on hostname differs, set `Add-on URL` explicitly during setup.

## Notes

- SIP, ISAPI, RTP, and WebRTC media handling stay inside the add-on.
- This integration owns Home Assistant entities and actions.
