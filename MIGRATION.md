# Migration Guide

## Upgrading to v0.4.0

Version 0.4.0 is a major release that rewrites the integration around the async `huckleberry-api` v0.2.x library. It introduces breaking changes to entity IDs, service names, and removes device actions. Follow the steps below to migrate your automations and dashboards.

---

## Breaking Changes

### 1. Services renamed (feeding → nursing)

All feeding/breastfeeding services have been renamed to use the term **nursing** to match the Huckleberry app's own terminology.

| Old service (≤ 0.3.x) | New service (0.4.0+) |
|---|---|
| `huckleberry.start_feeding` | `huckleberry.start_nursing` |
| `huckleberry.pause_feeding` | `huckleberry.pause_nursing` |
| `huckleberry.resume_feeding` | `huckleberry.resume_nursing` |
| `huckleberry.switch_feeding_side` | `huckleberry.switch_nursing_side` |
| `huckleberry.cancel_feeding` | `huckleberry.cancel_nursing` |
| `huckleberry.complete_feeding` | `huckleberry.complete_nursing` |

The `side` parameter and all other fields remain the same.

### 2. Entity IDs changed

#### Switches

| Old entity ID (≤ 0.3.x) | New entity ID (0.4.0+) |
|---|---|
| `switch.{child_name}_sleep_tracking` | `switch.{child_name}_sleep_timer` |
| `switch.{child_name}_feeding_left` | `switch.{child_name}_nursing_left` |
| `switch.{child_name}_feeding_right` | `switch.{child_name}_nursing_right` |

#### Sensors

| Old entity ID (≤ 0.3.x) | New entity ID (0.4.0+) | Notes |
|---|---|---|
| `sensor.{child_name}_sleep_status` | `sensor.{child_name}_sleep` | Renamed |
| `sensor.{child_name}_feeding_status` | `sensor.{child_name}_nursing` | Renamed |
| `sensor.{child_name}_last_diaper` | `sensor.{child_name}_diaper` | Renamed |
| `sensor.{child_name}_last_bottle` | `sensor.{child_name}_bottle` | Renamed |

#### Sensors removed

The following sensors have been removed. The data they provided has been moved to attributes on the main sensors listed above.

| Removed entity | Where to find the data now |
|---|---|
| `sensor.{child_name}_last_feeding_side` | `sensor.{child_name}_nursing` → attribute `last_side` |
| `sensor.{child_name}_previous_sleep_start` | `sensor.{child_name}_sleep` → attribute `last_sleep_start` |
| `sensor.{child_name}_previous_sleep_end` | `sensor.{child_name}_sleep` → attribute `last_sleep_end` |

### 3. Device actions removed

All 17 device actions have been removed. HA services (callable from automations and scripts) provide the same functionality with better automation support.

**Old device action:**
```yaml
action:
  - device_id: <child_device_id>
    domain: huckleberry
    type: start_sleep
```

**New service call:**
```yaml
action:
  - action: huckleberry.start_sleep
    data:
      device_id: <child_device_id>
```

See the [Services](#services) section of the README for the full list of available services.

### 4. Service calls now require `device_id`

Previously, a service call accepted either `device_id` or `child_uid`, and silently fell back to the first child if neither was provided. Both fallbacks have been removed.

Every service call must now include `device_id` — the HA device ID of the child's device. Use the device selector in the automation editor to pick the child device.

---

## New Features in v0.4.0

- **Calendar entity** (`calendar.{child_name}_events`): displays all historical events (sleep, feeding, diaper, growth) in HA's built-in calendar view.
- **Fully async**: no more blocking calls; the integration is now non-blocking throughout.
- **Orphan cleanup**: removing a child from the Huckleberry account will automatically remove the corresponding HA device and entities on next reload.

---

## Step-by-step Migration

1. **Update the integration** via HACS (or manually copy the new files).
2. **Restart Home Assistant**.
3. **Update automations**: find every `huckleberry.*_feeding*` service call and rename it to `huckleberry.*_nursing*` (see table above).
4. **Update dashboard cards**: replace entity IDs that changed (switches and sensors, see tables above).
5. **Replace device actions**: convert any device-action blocks to service calls (see example above).
6. **Update template/state references**: replace removed sensor entity IDs with attribute lookups on the renamed sensors.
