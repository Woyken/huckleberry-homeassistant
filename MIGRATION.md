# Migration Guide

## Upgrading to v0.4.0

Version 0.4.0 is a major release that moves the integration to the async `huckleberry-api` `0.2.3` library and simplifies the entity model. The main breaking changes are renamed nursing services, removed device actions, new service targeting rules, renamed entity IDs, and consolidated history sensors.

---

## Breaking Changes

### 1. Feeding services were renamed to nursing

The `0.3.x` breastfeeding services were renamed in `0.4.0` to match the current integration terminology.

| Old service (0.3.x) | New service (0.4.0+) |
|---|---|
| `huckleberry.start_feeding` | `huckleberry.start_nursing` |
| `huckleberry.pause_feeding` | `huckleberry.pause_nursing` |
| `huckleberry.resume_feeding` | `huckleberry.resume_nursing` |
| `huckleberry.switch_feeding_side` | `huckleberry.switch_nursing_side` |
| `huckleberry.cancel_feeding` | `huckleberry.cancel_nursing` |
| `huckleberry.complete_feeding` | `huckleberry.complete_nursing` |

Notes:

- `start_nursing` still accepts an optional `side` field.
- `resume_nursing` also accepts an optional `side` field.
- `child_uid` is no longer accepted on any service call. See the next section.

### 2. All service calls now target children by `device_id` only

In `0.3.x`, service handlers accepted either `device_id` or `child_uid`, and the handler code could fall back to the first child if neither resolved successfully.

In `0.4.0`, every service call must include `device_id`, and the integration raises a service validation error if that device cannot be resolved to a Huckleberry child.

This applies to all services, including sleep, nursing, diaper, growth, and bottle logging.

**Old style:**

```yaml
action:
  - action: huckleberry.start_feeding
    data:
      child_uid: abc123
      side: left
```

**New style:**

```yaml
action:
  - action: huckleberry.start_nursing
    data:
      device_id: <child_device_id>
      side: left
```

### 3. Device actions were removed

All device actions from `0.3.x` were removed in `0.4.0`. Use Home Assistant service calls in automations and scripts instead.

**Old device action:**

```yaml
action:
  - device_id: <child_device_id>
    domain: huckleberry
    type: start_sleep
```

**Replacement service call:**

```yaml
action:
  - action: huckleberry.start_sleep
    data:
      device_id: <child_device_id>
```

For old `start_feeding_left` and `start_feeding_right` device actions, use `huckleberry.start_nursing` with `side: left` or `side: right`.

### 4. Entity IDs changed

#### Switches

| Old entity ID (0.3.x) | New entity ID (0.4.0+) |
|---|---|
| `switch.{child_name}_sleep_tracking` | `switch.{child_name}_sleep_timer` |
| `switch.{child_name}_feeding_left` | `switch.{child_name}_nursing_left` |
| `switch.{child_name}_feeding_right` | `switch.{child_name}_nursing_right` |

#### Sensors

| Old entity ID (0.3.x) | New entity ID (0.4.0+) |
|---|---|
| `sensor.{child_name}_sleep_status` | `sensor.{child_name}_sleep` |
| `sensor.{child_name}_feeding_status` | `sensor.{child_name}_nursing` |
| `sensor.{child_name}_last_diaper` | `sensor.{child_name}_diaper` |

New entities added in `0.4.0`:

- `sensor.{child_name}_bottle`
- `calendar.{child_name}_events`

### 5. Sleep and nursing state values changed

The main activity sensors changed state values in `0.4.0`:

| Entity | Old active state | New active state |
|---|---|---|
| Sleep | `sleeping` | `active` |
| Nursing | `feeding` | `active` |

Paused and inactive remain `paused` and `none` when timer data is present.

If you have templates, automations, or dashboard conditional cards comparing sensor state strings, update those comparisons.

### 6. Several history sensors were removed and consolidated into attributes

The old standalone history sensors from `0.3.x` were removed in `0.4.0`. Their data now lives on the main `sleep` and `nursing` sensors.

| Removed entity (0.3.x) | Replacement in 0.4.0 |
|---|---|
| `sensor.{child_name}_last_feeding_side` | `sensor.{child_name}_nursing` attributes: `current_active_side`, `current_last_side`, or `previous_last_side` depending on session state |
| `sensor.{child_name}_previous_sleep_start` | `sensor.{child_name}_sleep` attribute `previous_start` |
| `sensor.{child_name}_previous_sleep_end` | No direct attribute. Use `sensor.{child_name}_sleep` attributes `previous_start` and `previous_duration` if you need to derive the end time in a template. |
| `sensor.{child_name}_previous_feed_start` | `sensor.{child_name}_nursing` attribute `previous_start` |

The consolidated attribute names are different from `0.3.x`. Common replacements include:

- Sleep current session: `current_start`, `current_end`
- Sleep history: `previous_start`, `previous_duration`
- Nursing current session: `current_start`, `current_left_duration`, `current_right_duration`, `current_active_side`, `current_last_side`
- Nursing history: `previous_start`, `previous_duration`, `previous_left_duration`, `previous_right_duration`, `previous_last_side`

Datetime attributes are now exposed as ISO 8601 strings instead of raw Unix timestamps or formatted local-time strings. Examples include `current_start`, `current_end`, `previous_start`, and diaper or bottle `time` attributes.

In Home Assistant templates, you can convert these values with `as_datetime`, for example:

```jinja
{{ "2026-03-12T08:30:00+00:00" | as_datetime }}
```

Duration attributes are now exposed as ISO 8601 duration strings instead of raw second counts or formatted text. Examples include `previous_duration`, `current_left_duration`, `current_right_duration`, `previous_left_duration`, and `previous_right_duration`.

In Home Assistant templates, you can convert these values with `as_timedelta`, for example:

```jinja
{{ "PT1H30M" | as_timedelta }}
```

### 7. Diaper, bottle, and growth sensors now behave like timestamp sensors

In `0.3.x`, several history-oriented sensors returned formatted text such as `No data`, `No changes logged`, or formatted local timestamps.

In `0.4.0`, these sensors expose Home Assistant timestamp sensor values instead:

- `sensor.{child_name}_diaper`
- `sensor.{child_name}_bottle`
- `sensor.{child_name}_growth`

Their states are timestamp values in Home Assistant rather than the old human-formatted strings. If you need to work with those states in templates, use datetime-aware handling instead of string comparisons.

---

## New Features in v0.4.0

- `calendar.{child_name}_events` adds a calendar view of historical sleep, feed, diaper, and growth events.
- `huckleberry.log_bottle` is a new service for logging bottle feeds with `amount`, `bottle_type`, and optional `units`.
- The integration is now fully async end-to-end.
- Orphaned child devices and entities are cleaned up automatically when a child is removed from the Huckleberry account and the integration reloads.

---

## Step-by-step Migration

1. Update the integration to `0.4.0`.
2. Restart Home Assistant.
3. Replace every `huckleberry.*feeding*` service call with the corresponding `*nursing*` service call.
4. Remove any `child_uid` fields from automation YAML and pass `device_id` instead.
5. Replace any removed device actions with service calls.
6. Update entity IDs in dashboards, templates, and automations:
   - `switch.{child_name}_sleep_tracking` → `switch.{child_name}_sleep_timer`
   - `switch.{child_name}_feeding_left` → `switch.{child_name}_nursing_left`
   - `switch.{child_name}_feeding_right` → `switch.{child_name}_nursing_right`
   - `sensor.{child_name}_sleep_status` → `sensor.{child_name}_sleep`
   - `sensor.{child_name}_feeding_status` → `sensor.{child_name}_nursing`
   - `sensor.{child_name}_last_diaper` → `sensor.{child_name}_diaper`
7. Update any state comparisons:
   - `sleeping` → `active`
   - `feeding` → `active`
8. Replace references to removed history sensors with the new attributes on `sensor.{child_name}_sleep` and `sensor.{child_name}_nursing`.
9. If you want bottle history or a calendar view, add the new `sensor.{child_name}_bottle` and `calendar.{child_name}_events` entities to your dashboard.
