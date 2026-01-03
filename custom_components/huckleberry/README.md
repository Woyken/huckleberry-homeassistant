# Huckleberry Home Assistant Integration

A custom Home Assistant integration that provides real-time baby sleep and feeding tracking using the Huckleberry app's Firebase backend.

## Features

- 🛌 **Sleep Tracking**: Real-time monitoring with < 1 second latency
- 🍼 **Feeding Tracking**: Left/right breast feeding with duration accumulation
- 🚼 **Diaper Changes**: Log pee, poo, both, or dry checks with color/consistency tracking
- 📏 **Growth Tracking**: Log weight, height, and head circumference measurements
- 👶 **Multiple Children Support**: Separate device for each child
- 📊 **Full Control**: Start, pause, resume, cancel, complete via switches and services
- ⚡ **Real-time Updates**: gRPC snapshot listeners for instant state changes
- 🎯 **Device Actions**: 17 device-specific actions for automations
- 📱 **App Sync**: All changes reflect immediately in Huckleberry app

## Installation

### HACS (Recommended)

1. Add this repository as a custom repository in HACS
2. Search for "Huckleberry" in HACS
3. Install the integration
4. Restart Home Assistant

### Manual Installation

1. Copy the `huckleberry_integration` folder to `config/custom_components/`
2. Rename it to `huckleberry`
3. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services
2. Click "+ ADD INTEGRATION"
3. Search for "Huckleberry"
4. Enter your Huckleberry account email and password
5. Click Submit

## Entities

### Per Child Device

Each child gets a dedicated device with 7 entities. The device includes the child's profile picture (if set in Huckleberry app) which appears in the device page.

1. **Child Profile Sensor**: `sensor.{child_name}_profile`
   - State: Child's name
   - Attributes:
     - `uid`: Child's unique identifier
     - `name`: Child's name
     - `birthday`: Birth date (YYYY-MM-DD format)
     - `picture`: URL to profile picture (Firebase Storage)

2. **Sleep Sensor**: `sensor.{child_name}_sleep_status`
   - State: `sleeping`, `paused`, or `none`
   - Attributes:
     - `is_paused`: Whether sleep is paused (when active)
     - `sleep_start`: Current sleep start time (if active)
     - `timer_start_time`: Timer start timestamp for chronometer
     - `timer_end_time`: Timer end timestamp when timer is paused
     - `last_sleep_duration_seconds`: Last completed sleep duration
     - `last_sleep_start`: When last sleep started

3. **Sleep Switch**: `switch.{child_name}_sleep_tracking`
   - Turn ON: Starts new sleep session
   - Turn OFF: Completes sleep and saves to history
   - Attributes:
     - `start_time`: When current sleep started
     - `last_sleep_duration_minutes`: Last sleep duration

4. **Feeding Sensor**: `sensor.{child_name}_feeding_status`
   - State: `feeding`, `paused`, or `none`
   - Attributes:
     - `feeding_start`: Current feeding start time (if active)
     - `left_duration_seconds`: Accumulated left breast duration
     - `right_duration_seconds`: Accumulated right breast duration
     - `last_side`: Which side is currently active
     - `last_nursing_*`: Last completed feeding details

5. **Last Feeding Side Sensor**: `sensor.{child_name}_last_feeding_side`
   - State: `Left`, `Right`, or `Unknown`
   - Shows current side if feeding, paused side if paused, or last side from history if stopped.

6. **Previous Sleep End Sensor**: `sensor.{child_name}_previous_sleep_end`
   - State: Timestamp of when the last sleep session ended.
   - Device Class: `timestamp`

7. **Previous Feed Start Sensor**: `sensor.{child_name}_previous_feed_start`
   - State: Timestamp of when the last feeding session started.
   - Device Class: `timestamp`

8. **Feeding Left Switch**: `switch.{child_name}_feeding_left`
   - Turn ON: Starts feeding on left breast
   - Turn OFF: Completes and saves feeding
   - Attributes:
     - `side`: "left"
     - `duration_seconds`: Current session right duration
     - `feeding_start`: Session start time

9. **Feeding Right Switch**: `switch.{child_name}_feeding_right`
   - Turn ON: Starts feeding on right breast
   - Turn OFF: Completes and saves feeding
   - Attributes:
     - `side`: "right"
     - `duration_seconds`: Current session right duration
     - `feeding_start`: Session start time

10. **Growth Sensor**: `sensor.{child_name}_growth`
   - State: Last measurement timestamp (YYYY-MM-DD HH:MM) or "No data"
   - Attributes:
     - `weight`: Weight with units (e.g., "5.2 kg")
     - `height`: Height with units (e.g., "65.5 cm")
     - `head_circumference`: Head circumference with units (e.g., "42.3 cm")
     - `weight_value`: Raw weight value
     - `height_value`: Raw height value
     - `head_value`: Raw head circumference value
     - `units`: "metric" or "imperial"
     - `last_updated`: Unix timestamp of measurement

### Account Level

**Children Sensor**: `sensor.huckleberry_children`
- State: Number of children
- Attributes:
  - `children`: Full array with uid, name, birthday, picture for each child
  - `child_ids`: Array of child UIDs
  - `child_names`: Array of child names

## Services

All services support device selection via dropdown or explicit `child_uid` (advanced).

### Sleep Services

- **`huckleberry.start_sleep`**: Start new sleep session
- **`huckleberry.pause_sleep`**: Pause current sleep (preserves timer)
- **`huckleberry.resume_sleep`**: Resume paused sleep
- **`huckleberry.cancel_sleep`**: Cancel sleep without saving to history
- **`huckleberry.complete_sleep`**: Complete and save sleep with interval

### Feeding Services

- **`huckleberry.start_feeding`**: Start feeding session (specify `side: left` or `right`)
- **`huckleberry.pause_feeding`**: Pause current feeding
- **`huckleberry.resume_feeding`**: Resume paused feeding
- **`huckleberry.switch_feeding_side`**: Switch between left/right (accumulates duration)
- **`huckleberry.cancel_feeding`**: Cancel feeding without saving to history
- **`huckleberry.complete_feeding`**: Complete and save feeding to lastNursing

### Diaper Services

- **`huckleberry.log_diaper_pee`**: Log diaper change with pee only
- **`huckleberry.log_diaper_poo`**: Log poo with optional color/consistency
  - Colors: yellow, green, brown, black, red
  - Consistency: runny, soft, solid, hard
- **`huckleberry.log_diaper_both`**: Log both pee and poo with optional color/consistency
- **`huckleberry.log_diaper_dry`**: Log dry diaper check

### Growth Services

- **`huckleberry.log_growth`**: Log weight, height, and head circumference
  - Parameters: `weight`, `height`, `head`, `units` (metric/imperial)
  - All measurements optional (log any combination)
  - See [GROWTH_TRACKING.md](GROWTH_TRACKING.md) for details

### Service Call Examples

Using device selector (recommended):
```yaml
service: huckleberry.start_sleep
data:
  device_id: <select child device from dropdown>
```

Using explicit child_uid (advanced):
```yaml
service: huckleberry.start_feeding
data:
  child_uid: VZiSnxmU3KawWzsSLTqyuPTlsuX2
  side: left
```

## Device Actions

When creating automations, select a child device and choose from 17 actions:

**Sleep Actions:**
- Start Sleep
- Pause Sleep
- Resume Sleep
- Cancel Sleep
- Complete Sleep

**Feeding Actions:**
- Start Feeding (Left)
- Start Feeding (Right)
- Pause Feeding
- Resume Feeding
- Switch Feeding Side
- Cancel Feeding
- Complete Feeding

**Diaper Actions:**
- Log Diaper - Pee
- Log Diaper - Poo
- Log Diaper - Both
- Log Diaper - Dry Check

**Growth Actions:**
- Log Growth Measurements

## Example Automations

### Sleep Notifications

Notify when baby wakes up:
```yaml
automation:
  - alias: "Baby Woke Up"
    trigger:
      - platform: state
        entity_id: binary_sensor.baby_sleep_status
        from: "on"
        to: "off"
    action:
      - service: notify.mobile_app
        data:
          title: "Baby is awake!"
          message: "Baby slept for {{ (state_attr('binary_sensor.baby_sleep_status', 'last_sleep_duration_seconds') / 60) | round(0) }} minutes"
```

### Night Light Control

Turn on night light when sleeping:
```yaml
automation:
  - alias: "Baby Sleep Night Light"
    trigger:
      - platform: state
        entity_id: binary_sensor.baby_sleep_status
        to: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.nursery_night_light
        data:
          brightness_pct: 10
```

### Feeding Timer Reminder

Notify when feeding exceeds 30 minutes:
```yaml
automation:
  - alias: "Long Feeding Alert"
    trigger:
      - platform: state
        entity_id: binary_sensor.baby_feeding_status
        to: "on"
        for:
          minutes: 30
    action:
      - service: notify.mobile_app
        data:
          title: "Feeding Duration"
          message: "Baby has been feeding for 30+ minutes"
```

### Switch-Based Tracking

Quick sleep toggle from dashboard:
```yaml
type: entities
title: Baby Sleep
entities:
  - entity: switch.baby_sleep_tracking
  - entity: binary_sensor.baby_sleep_status
    name: Current Status
```

### Device Action Automation

Use device actions in automations:
```yaml
automation:
  - alias: "Bedtime Routine"
    trigger:
      - platform: time
        at: "19:00:00"
    action:
      - device_id: <child_device_id>
        domain: huckleberry
        type: start_sleep
```

## How It Works

The integration connects to Huckleberry's Firebase backend using the official Firebase SDK:

1. **Authentication**: Uses Firebase Identity Toolkit API with email/password
2. **Data Access**: Connects to Firestore via gRPC protocol (not REST API)
3. **Real-time Updates**: Firestore snapshot listeners provide < 1 second latency
4. **Data Structure**: Monitors `sleep/{child_uid}` and `feed/{child_uid}` documents
5. **State Determination**:
   - Sleep: `timer.active = true` and `timer.paused = false`
   - Feeding: Same logic with side-specific duration tracking

### Technical Architecture

- **Backend**: Firebase Firestore (project: simpleintervals)
- **Protocol**: gRPC over HTTP/2 with Protocol Buffers
- **SDK**: `google-cloud-firestore` Python library
- **Update Method**: Real-time snapshot listeners (push notifications)
- **Latency**: 0.2-1.0 seconds measured
- **IoT Class**: `cloud_push` (instant updates, no polling)

### Key Implementation Details

**Sleep Tracking:**
- `timerStartTime`: Stored in **milliseconds** (multiply time.time() by 1000)
- Duration: Calculated as `(now - timerStartTime/1000)` seconds
- Intervals: Saved to `sleep/{uid}/intervals` subcollection

**Feeding Tracking:**
- `timerStartTime`: Stored in **seconds** (unlike sleep!)
- Duration: Accumulated per side (`leftDuration`, `rightDuration`)
- Side switching: Accumulates elapsed time to current side before switching
- History: Saved to `feed/{uid}/prefs.lastNursing`

## API Details

- **Firebase Project**: simpleintervals
- **API Key**: AIzaSyApGVHktXeekGyAt-G6dIeWHUkq2oXqcjg
- **Auth Endpoint**: identitytoolkit.googleapis.com
- **Firestore**: firestore.googleapis.com (gRPC)
- **Collections**: `users`, `childs`, `sleep`, `feed`

## Security & Privacy

- Credentials stored securely in Home Assistant's encrypted config entry storage
- All communication encrypted via TLS (HTTPS/gRPC)
- Uses official Firebase SDK with proper authentication
- Read/write access to your own Huckleberry data only
- No third-party data sharing
- Full bidirectional sync with Huckleberry app

## Troubleshooting

### Integration fails to load

- Verify email and password are correct
- Ensure at least one child exists in Huckleberry account
- Check HA logs: Settings → System → Logs
- Look for "huckleberry" or Firebase authentication errors

### Real-time updates not working

- Check internet connectivity
- Verify Firestore listeners are active (logs show "Setting up real-time listener")
- Integration will auto-reconnect on network issues
- Try reloading the integration

### Authentication errors (400 Bad Request)

- Password may be incorrect
- Account may require 2FA (not currently supported)
  - Try logging into Huckleberry app first
  - Remove and re-add integration

### Entities showing "unavailable"

- Check coordinator.last_update_success in developer tools
- Verify child exists in account
- Check Firebase connectivity in logs
- Reload integration to reinitialize listeners

### Sleep/feeding not saving to history

- Ensure you use "Complete" action (not just cancel/stop)
- Check Huckleberry app to verify data appears
- Look for Firestore write errors in logs
- Timer must have valid timerStartTime

## Automation Examples

### Sleep Notification with Chronometer

Create actionable notifications showing live elapsed sleep time with Stop/Pause buttons.

**Quick Setup**: See `baby_sleep_notification.yaml` for a ready-to-use template.

**Full Guide**: Read `NOTIFICATION_SETUP.md` for complete setup instructions.

**Example notification**:
```yaml
data:
  title: "Baby sleep"
  message: "Sleep since 12:24"
  data:
    chronometer: true
    when: "{{ state_attr('binary_sensor.emma_sleep_status', 'timer_start_time') }}"
    notification_icon: "mdi:sleep"
    actions:
      - action: STOP
        title: Stop
      - action: PAUSE
        title: Pause
```

**Available Files**:
- `baby_sleep_notification.yaml` - Ready-to-use template (just customize names)
- `automation_examples.yaml` - 5 complete examples with variations
- `NOTIFICATION_SETUP.md` - Comprehensive setup guide with troubleshooting

## Known Limitations- Requires active internet connection (cloud-based)
- Authentication token expires after 1 hour (auto-refreshed)
- Only tracks sleep and breast feeding (bottle/solids not implemented)
- Timezone offset hardcoded to -120 minutes (can be customized in code)
- No offline mode

## Dependencies

- `google-cloud-firestore>=2.11.0`: Official Firebase SDK
- Home Assistant Core: 2023.1+ (uses async_forward_entry_setups)

## Future Enhancements

- [ ] Bottle feeding tracking
- [ ] Diaper tracking
- [ ] Solid food tracking
- [ ] Sleep quality metrics and statistics
- [ ] Configurable timezone offset
- [ ] 2FA support for authentication
- [ ] Offline mode with sync queue
- [ ] Multiple accounts support

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Disclaimer

This integration is not affiliated with, endorsed by, or connected to Huckleberry in any way. It is an independent project that uses the Huckleberry app's backend API for personal use only.

Use at your own risk. The integration accesses your Huckleberry account data, and while it only reads data, you should be aware of the potential security implications.

## Credits

Created by reverse engineering the Huckleberry Android app using:
- **HTTP Toolkit**: Network traffic analysis and HAR file capture
- **JADX**: APK decompilation and Java source extraction
- **Firebase SDK**: Official Google Cloud Firestore Python library
- **gRPC Protocol Analysis**: Understanding Firebase's native protocol

Key technical discoveries:
- App uses Firebase Android SDK (not REST API)
- gRPC over HTTP/2 with Protocol Buffers encoding
- Real-time updates via Firestore snapshot listeners
- Different timestamp formats for sleep (ms) vs feeding (seconds)

## License

MIT License - See LICENSE file for details

---

**Version**: 1.0.0
**Last Updated**: November 2025
**Platforms**: binary_sensor, switch, sensor
**IoT Class**: cloud_push
