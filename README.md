# Huckleberry Home Assistant Integration

Home Assistant custom integration for the Huckleberry baby tracking app.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Woyken&repository=huckleberry-homeassistant&category=integration)

## Overview

This integration provides real-time baby tracking in Home Assistant by connecting to Huckleberry's Firebase backend using the [`huckleberry-api`](https://pypi.org/project/huckleberry-api/) Python library.

## Features

- 💤 **Sleep Tracking**: Sensors, switches, and automation actions
- 🍼 **Feeding Tracking**: Left/right side tracking with switches, bottle feeding with amount and type
- 🧷 **Diaper Changes**: Log pee, poo, both, or dry checks
- 📏 **Growth Measurements**: Track weight, height, head circumference
- 🔄 **Real-time Sync**: Instant updates via Firebase listeners
- 🤖 **Automations**: Device actions for advanced automations
- 👶 **Multi-child Support**: Separate devices per child

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Huckleberry Baby Tracker"
3. Click Install
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/huckleberry` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Huckleberry"
4. Enter your Huckleberry account email and password
5. Click Submit

## Entities Created

### Per Child:
- **Sensors**:
  - `sensor.{child_name}_sleep_status` - Sleep status (sleeping, paused, none)
  - `sensor.{child_name}_feeding_status` - Feeding status (feeding, paused, none)
  - `sensor.{child_name}_profile` - Child profile information
  - `sensor.{child_name}_growth` - Latest growth measurements
  - `sensor.{child_name}_last_bottle` - Last bottle feeding (time, amount, type)

- **Switches** (3):
  - `switch.{child_name}_sleep` - Start/stop sleep tracking
  - `switch.{child_name}_feeding_left` - Left side feeding
  - `switch.{child_name}_feeding_right` - Right side feeding

- **Calendar** (1):
  - `calendar.{child_name}_events` - All historical events (sleep, feeding, diaper, growth)

### Global:
- `sensor.huckleberry_children` - Number of children

## Services

All services support device selection for easy use in automations:

### Sleep Tracking
- `huckleberry.start_sleep`
- `huckleberry.pause_sleep`
- `huckleberry.resume_sleep`
- `huckleberry.cancel_sleep`
- `huckleberry.complete_sleep`

### Feeding Tracking
- `huckleberry.start_feeding`
- `huckleberry.pause_feeding`
- `huckleberry.resume_feeding`
- `huckleberry.switch_feeding_side`
- `huckleberry.cancel_feeding`
- `huckleberry.complete_feeding`
- `huckleberry.log_bottle` - Log bottle feeding (formula or breastmilk) with amount in oz or ml

### Diaper Changes
- `huckleberry.log_diaper_pee`
- `huckleberry.log_diaper_poo`
- `huckleberry.log_diaper_both`
- `huckleberry.log_diaper_dry`

### Growth Tracking
- `huckleberry.log_growth`

## Calendar

Each child gets a calendar entity that displays all historical events:

- **💤 Sleep events**: Shows duration and timing of all sleep sessions
- **🍼 Feeding events**: Shows duration, left/right side information
- **🩲 Diaper changes**: Shows type (pee/poo/both/dry) and details
- **📏 Growth measurements**: Shows weight, height, head circumference

The calendar can be added to dashboards and used in automations. Events are automatically fetched when you view the calendar for a specific date range.

### Adding to Dashboard

Add the calendar card to your dashboard:
```yaml
type: calendar
entities:
  - calendar.baby_name_events
```

## Example Automations

See `automation_examples.yaml` for complete examples.

### Bedtime Notification
```yaml
automation:
  - alias: "Baby Sleep Started"
    trigger:
      - platform: state
        entity_id: sensor.baby_name_sleep_status
        to: "sleeping"
    action:
      - service: notify.mobile_app
        data:
          message: "Baby started sleeping"
```

### Feeding Timer Alert
```yaml
automation:
  - alias: "Feeding Duration Alert"
    trigger:
      - platform: state
        entity_id: sensor.baby_name_feeding_status
        to: "feeding"
        for:
          minutes: 20
    action:
      - service: notify.mobile_app
        data:
          message: "Baby has been feeding for 20 minutes"
```

### Log Bottle Feeding
```yaml
automation:
  - alias: "Log Bottle at Scheduled Time"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: huckleberry.log_bottle
        target:
          device_id: YOUR_DEVICE_ID  # Select your child's device
        data:
          amount: 4.0
          bottle_type: Formula
          units: oz
```

## Device Actions

The integration provides device actions for use in device-based automations:
- Sleep actions: start, pause, resume, cancel, complete
- Feeding actions: start left/right, pause, resume, switch side, cancel, complete
- Diaper actions: log pee, poo, both, dry
- Growth actions: log growth
- Bottle actions: log bottle feeding

## Documentation

- **Installation Guide**: See `INSTALLATION.md`
- **Quick Reference**: See `QUICK_REFERENCE.md`
- **Growth Tracking**: See `GROWTH_TRACKING.md`
- **Notifications Setup**: See `NOTIFICATION_SETUP.md`
- **Testing Guide**: See `TESTING.md`

## Requirements

- Home Assistant 2023.1 or newer
- Huckleberry account with active subscription
- `huckleberry-api>=0.1.18` (automatically installed)

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Related Projects

- [huckleberry-api](https://github.com/Woyken/huckleberry-api) - Python API library used by this integration

## Disclaimer

This is an unofficial, community-developed integration. Not affiliated with, endorsed by, or connected to Huckleberry Labs Inc.

## License

MIT License
