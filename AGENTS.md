# AI Agent Context Guide - Huckleberry Home Assistant Integration

## Project Overview

This is a **Home Assistant custom integration** for the Huckleberry baby tracking app. It provides real-time sleep, feeding, diaper, and growth tracking by using the [`huckleberry-api`](https://pypi.org/project/huckleberry-api/) Python library to connect to Huckleberry's Firebase backend.

**Critical Context**: This integration wraps the `huckleberry-api` library and adapts it for Home Assistant's architecture. The API handles all Firebase operations, while this integration provides HA-specific features like entities, services, automations, and real-time updates through coordinators.

## Related Documentation

- **[Project Overview](../AGENTS.md)** - High-level context, history, decompiled source analysis
- **[API Library](../huckleberry-api/AGENTS.md)** - Underlying Firebase operations and data structures

## Project Purpose

This integration provides:
- Home Assistant entities for baby tracking (sensors, switches)
- Services for controlling tracking from automations
- Device actions for advanced automation scenarios
- Real-time updates via coordinator and Firebase listeners
- Multi-child support with device grouping
- HACS installation support

## Architecture

### Technology Stack

**Home Assistant:**
- Custom Component (local integration)
- Config Flow for UI configuration
- Data Update Coordinator pattern
- Async/await architecture
- Real-time entity updates

**Platforms:**
- `switch`: Sleep tracking + left/right feeding switches per child
- `sensor`: Sleep/feeding status + Children count + child profile + growth sensors
- `device_action`: 18 device-specific automation actions

**External Dependencies:**
- `huckleberry-api>=0.1.14` - Firebase operations
- `google-cloud-firestore>=2.11.0` - Required by huckleberry-api

### Integration Structure

```
custom_components/huckleberry/
├── __init__.py              # Integration setup, coordinator, service registration
├── api.py                   # Legacy API (deprecated - will be removed)
├── config_flow.py           # Configuration UI flow
├── const.py                 # Constants (DOMAIN, PLATFORMS)
├── switch.py                # Sleep + Left/Right feeding switches (3 per child)
├── sensor.py                # Sleep/Feed status + Profile + Growth sensors (4 per child) + Children count
├── device_action.py         # 17 device actions for automations
├── services.yaml            # Service definitions with device selectors
├── manifest.json            # Integration metadata, dependencies
├── strings.json             # UI strings for config flow
├── translations/            # Localization files
│   └── en.json
├── README.md                # User installation guide
└── AGENTS.md                # This file
```

### Key Classes

**`HuckleberryDataUpdateCoordinator`** (`__init__.py`):
- Extends `DataUpdateCoordinator` from Home Assistant
- Manages data updates for all entities
- Sets up real-time Firebase listeners via `async_setup_listeners()`
- Stores data in `_realtime_data` dict by child_uid
- Structure: `{child_uid: {"sleep_status": {...}, "feed_status": {...}, "health_status": {...}}}`
- Provides `get_sleep_status()`, `get_feed_status()`, `get_health_status()` helper methods
- Handles listener cleanup on unload

**Service Implementation Pattern**:

Services use device selector for user convenience:

1. **services.yaml**: Define `device_id` field with `selector: device: integration: huckleberry`
2. **__init__.py**: `_get_child_uid_from_call()` extracts child_uid from device_id
3. **Priority**: Explicit `child_uid` > device_id > first child fallback
4. **Device lookup**: Uses `device_registry.async_get()` and extracts from identifiers

**Entity Device Info Pattern**:

All child-specific entities include `device_info`:

```python
@property
def device_info(self) -> dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, self.child_uid)},
        "name": self.child_name,
        "manufacturer": "Huckleberry",
        "configuration_url": self.profile_picture_url,  # If available
    }
```

This groups entities under one device per child in HA UI.

## Entity Details

### Sensors (4 per child)

**`sensor.{child_name}_sleep_status`**:
- State: `sleeping`, `paused`, `none`
- Attributes: `is_paused`, `sleep_start`, `timer_start_time`, `timer_end_time`, `last_sleep_start`, `last_sleep_duration_seconds`
- Device class: `enum`
- Updates: Real-time via sleep listener

**`sensor.{child_name}_feeding_status`**:
- State: `feeding`, `paused`, `none`
- Attributes: `is_paused`, `feeding_start`, `left_duration_seconds`, `right_duration_seconds`, `last_side`
- Device class: `enum`
- Updates: Real-time via feed listener

### Switches (3 per child)

**`switch.{child_name}_sleep`**:
- State: `on` (sleep tracking active) / `off` (not tracking)
- Actions: Turn on = start sleep, Turn off = complete sleep
- Updates: Real-time via sleep listener

**`switch.{child_name}_feeding_left`**:
- State: `on` (left side feeding active) / `off` (not feeding left)
- Actions: Turn on = start/switch to left, Turn off = stop/switch away
- Updates: Real-time via feed listener

**`switch.{child_name}_feeding_right`**:
- State: `on` (right side feeding active) / `off` (not feeding right)
- Actions: Turn on = start/switch to right, Turn off = stop/switch away
- Updates: Real-time via feed listener

### Sensors (2 per child + 1 global)

**`sensor.{child_name}_profile`**:
- State: Child's name
- Attributes: `child_uid`, `birthdate`, `profile_picture`
- Icon: `mdi:account-child`
- Updates: On coordinator refresh

**`sensor.{child_name}_growth`**:
- State: Last measurement timestamp (or "No measurements")
- Attributes: `weight`, `weight_unit`, `height`, `height_unit`, `head_circumference`, `head_unit`
- Icon: `mdi:human-baby-changing-table`
- Updates: Real-time via health listener

**`sensor.huckleberry_children`**:
- State: Number of children
- Attributes: List of children with metadata (uid, name, birthdate, picture)
- Icon: `mdi:account-multiple`
- Updates: On coordinator refresh

## Services

All services support device selector for easy automation creation.

### Sleep Services

**`huckleberry.start_sleep`**:
- Starts sleep tracking for a child
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.pause_sleep`**:
- Pauses active sleep tracking
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.resume_sleep`**:
- Resumes paused sleep tracking
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.cancel_sleep`**:
- Cancels sleep without saving to history
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.complete_sleep`**:
- Completes sleep and saves to history
- Parameters: `device_id` (optional), `child_uid` (optional)

### Feeding Services

**`huckleberry.start_feeding`**:
- Starts feeding on specified side
- Parameters: `device_id` (optional), `child_uid` (optional), `side` (left/right, required)

**`huckleberry.pause_feeding`**:
- Pauses active feeding
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.resume_feeding`**:
- Resumes paused feeding
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.switch_feeding_side`**:
- Switches to opposite feeding side (auto-resumes)
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.cancel_feeding`**:
- Cancels feeding without saving to history
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.complete_feeding`**:
- Completes feeding and saves to history
- Parameters: `device_id` (optional), `child_uid` (optional)

### Diaper Services

**`huckleberry.log_diaper_pee`**:
- Logs a pee-only diaper change
- Parameters: `device_id` (optional), `child_uid` (optional)

**`huckleberry.log_diaper_poo`**:
- Logs a poo-only diaper change
- Parameters: `device_id` (optional), `child_uid` (optional), `color` (optional), `consistency` (optional)
- Color options: yellow, green, brown, black, red
- Consistency options: runny, soft, solid, hard

**`huckleberry.log_diaper_both`**:
- Logs a diaper change with both pee and poo
- Parameters: `device_id` (optional), `child_uid` (optional), `color` (optional), `consistency` (optional)

**`huckleberry.log_diaper_dry`**:
- Logs a dry diaper check (no change needed)
- Parameters: `device_id` (optional), `child_uid` (optional)

### Growth Service

**`huckleberry.log_growth`**:
- Logs growth measurements
- Parameters: `device_id` (optional), `child_uid` (optional), `weight` (optional), `weight_units` (kg/lbs), `height` (optional), `height_units` (cm/in), `head` (optional), `head_units` (hcm/hin)
- At least one measurement (weight, height, or head) is required

## Device Actions

Device actions appear in automation UI when selecting a device trigger/condition/action.

### Sleep Actions (5)
1. `start_sleep` - Start sleep tracking
2. `pause_sleep` - Pause sleep tracking
3. `resume_sleep` - Resume sleep tracking
4. `cancel_sleep` - Cancel sleep tracking
5. `complete_sleep` - Complete sleep tracking

### Feeding Actions (6)
7. `start_feeding_left` - Start feeding on left side
8. `start_feeding_right` - Start feeding on right side
9. `pause_feeding` - Pause feeding
10. `resume_feeding` - Resume feeding
11. `switch_feeding_side` - Switch to opposite side
12. `cancel_feeding` - Cancel feeding
13. `complete_feeding` - Complete feeding

### Diaper Actions (4)
14. `log_diaper_pee` - Log pee diaper
15. `log_diaper_poo` - Log poo diaper
16. `log_diaper_both` - Log pee and poo diaper
17. `log_diaper_dry` - Log dry diaper check

### Growth Action (1)
18. `log_growth` - Log growth measurements

**Total**: 18 device actions

## Critical Implementation Rules

### 1. Async/Await Pattern

**Home Assistant requires async**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Huckleberry from a config entry."""
    # Blocking API calls must use executor
    api = await hass.async_add_executor_job(
        HuckleberryAPI, entry.data["email"], entry.data["password"]
    )
    await hass.async_add_executor_job(api.authenticate)
```

**All service handlers must be async**:
```python
async def async_start_sleep(call: ServiceCall) -> None:
    """Handle the start_sleep service call."""
    child_uid = _get_child_uid_from_call(call)
    await hass.async_add_executor_job(api.start_sleep, child_uid)
```

### 2. Coordinator Update Pattern

**Real-time listeners should be the sole source of truth**:
```python
# GOOD - Listener updates coordinator automatically
def _handle_sleep_update(doc_snapshot, changes, read_time):
    sleep_data = doc_snapshot[0].to_dict() if doc_snapshot else None
    coordinator._realtime_data[child_uid]["sleep_status"] = sleep_data
    hass.async_create_task(coordinator.async_set_updated_data(coordinator.data))

# BAD - Don't mix manual refresh with real-time updates
await hass.async_add_executor_job(api.start_sleep, child_uid)
await coordinator.async_request_refresh()  # Don't do this!
```

**Reason**: Manual refresh fetches stale data before listener processes the update.

### 3. Device Selector Implementation

**Service definition** (services.yaml):
```yaml
start_sleep:
  name: Start Sleep
  description: Start sleep tracking
  fields:
    device_id:
      name: Child
      description: Select which child to track
      required: false
      selector:
        device:
          integration: huckleberry
    child_uid:
      name: Child UID
      description: Direct child UID (overrides device selection)
      required: false
      example: "abc123def456"
```

**Service handler** (__init__.py):
```python
def _get_child_uid_from_call(call: ServiceCall) -> str:
    """Extract child_uid from service call."""
    # Priority: explicit child_uid > device_id > first child
    if "child_uid" in call.data:
        return call.data["child_uid"]

    if "device_id" in call.data:
        device = device_registry.async_get(call.data["device_id"])
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                return identifier[1]  # child_uid

    # Fallback to first child
    children = coordinator.data.get("children", [])
    return children[0]["uid"] if children else None
```

### 4. Entity Update Mechanism

**Entity should read from coordinator**:
```python
@property
def is_on(self) -> bool:
    """Return true if sleep is active."""
    sleep_status = self.coordinator.get_sleep_status(self.child_uid)
    if not sleep_status or "timer" not in sleep_status:
        return False
    return sleep_status["timer"].get("active", False)
```

**Coordinator callback triggers entity update**:
```python
class HuckleberrySleepSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a Huckleberry sleep switch."""

    def __init__(self, coordinator, child_uid, child_name):
        """Initialize the switch."""
        super().__init__(coordinator)
        self.child_uid = child_uid
        # Entity automatically updates when coordinator.async_set_updated_data() is called
```

### 5. Config Flow Data Storage

**Store credentials in config entry**:
```python
async def async_step_user(self, user_input=None):
    """Handle the initial step."""
    if user_input is not None:
        # Validate credentials
        api = await self.hass.async_add_executor_job(
            HuckleberryAPI, user_input["email"], user_input["password"]
        )

        try:
            await self.hass.async_add_executor_job(api.authenticate)
        except Exception as err:
            return self.async_show_form(
                step_id="user",
                data_schema=DATA_SCHEMA,
                errors={"base": "invalid_auth"}
            )

        # Store in config entry (encrypted by HA)
        return self.async_create_entry(
            title="Huckleberry",
            data=user_input
        )
```

**Access credentials from config entry**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    email = entry.data["email"]
    password = entry.data["password"]
    # Use credentials...
```

## Common Pitfalls & Solutions

### Pitfall 1: Mixing Blocking and Async Code

**Wrong**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = HuckleberryAPI(entry.data["email"], entry.data["password"])
    api.authenticate()  # Blocks event loop!
```

**Result**: Home Assistant freezes, watchdog warnings

**Right**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = await hass.async_add_executor_job(
        HuckleberryAPI, entry.data["email"], entry.data["password"]
    )
    await hass.async_add_executor_job(api.authenticate)
```

### Pitfall 2: Not Cleaning Up Listeners

**Wrong**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Setup listeners but no cleanup
    await coordinator.async_setup_listeners()
    return True
```

**Result**: Listeners stay active after unload, memory leak

**Right**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await coordinator.async_setup_listeners()

    async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """Unload a config entry."""
        # Clean up listeners
        await hass.async_add_executor_job(coordinator.api.stop_all_listeners)
        # Unload platforms
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
        return unload_ok

    entry.async_on_unload(async_unload_entry)
    return True
```

### Pitfall 3: Service Not Found

**Wrong**:
```python
# Forgot to register service
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Setup coordinator and platforms...
    return True
```

**Result**: "Service huckleberry.start_sleep not found"

**Right**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Setup coordinator...

    # Register all services
    hass.services.async_register(DOMAIN, "start_sleep", async_start_sleep)
    hass.services.async_register(DOMAIN, "pause_sleep", async_pause_sleep)
    # ... register all services

    return True
```

### Pitfall 4: Entity Not Updating

**Wrong**:
```python
# Entity caches value
@property
def is_on(self) -> bool:
    """Return true if sleep is active."""
    return self._is_on  # Stale value
```

**Result**: Entity shows old state even after real-time update

**Right**:
```python
# Entity reads from coordinator
@property
def is_on(self) -> bool:
    """Return true if sleep is active."""
    sleep_status = self.coordinator.get_sleep_status(self.child_uid)
    if not sleep_status or "timer" not in sleep_status:
        return False
    return sleep_status["timer"].get("active", False)

# Coordinator triggers update
def _handle_sleep_update(doc_snapshot, changes, read_time):
    # Update data
    coordinator._realtime_data[child_uid]["sleep_status"] = sleep_data
    # Notify entities
    hass.async_create_task(coordinator.async_set_updated_data(coordinator.data))
```

### Pitfall 5: Device Not Showing in Automations

**Wrong**:
```python
# Entity missing device_info
class HuckleberrySleepSwitch(CoordinatorEntity, SwitchEntity):
    def __init__(self, coordinator, child_uid, child_name):
        super().__init__(coordinator)
        self.child_uid = child_uid
        # No device_info property
```

**Result**: Entities not grouped, device selector doesn't work

**Right**:
```python
class HuckleberrySleepSwitch(CoordinatorEntity, SwitchEntity):
    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.child_uid)},
            "name": self.child_name,
            "manufacturer": "Huckleberry",
        }
```

### Pitfall 6: Forgetting to Forward Platform Setup

**Wrong**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Setup coordinator...
    # Forgot to setup platforms!
    return True
```

**Result**: No entities created

**Right**:
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Setup coordinator...

    # Forward setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True
```

## Home Assistant Testing Workflow

### Development Cycle

1. **Edit code** in `custom_components/huckleberry/`
2. **Reload integration**: Developer Tools → YAML → Reload Custom Integrations
3. **Check logs**: Settings → System → Logs (filter: huckleberry)
4. **Verify entities**: Developer Tools → States
5. **Test services**: Developer Tools → Services
6. **Check app sync**: Open Huckleberry app and verify changes appear

### Testing Real-time Updates

1. Start tracking in HA (switch or service)
2. Verify appears in Huckleberry app
3. Pause in Huckleberry app
4. Verify HA entity updates (should be near-instant)
5. Complete in HA
6. Verify appears in app history

### Debug Logging

Enable detailed logging in `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.huckleberry: debug
    huckleberry_api: debug
    google.cloud.firestore: debug
```

### Common Log Messages

**Success**:
```
Setting up Huckleberry integration
Setting up real-time listener for child ABC123
Calling start_sleep for child ABC123
Sleep status updated for child ABC123
```

**Warnings**:
```
Missing timerStartTime for feeding
No active sleep to complete for child ABC123
```

**Errors**:
```
Failed to authenticate: 400 INVALID_PASSWORD
Failed to get children: [Errno -2] Name or service not known
Error in sleep listener callback: ...
```

## Performance Considerations

### Real-time Listeners

**Per Child**:
- 1 sleep listener (`sleep/{child_uid}`)
- 1 feed listener (`feed/{child_uid}`)
- 1 health listener (`health/{child_uid}`)
- Total: 3 persistent gRPC connections

**Scaling**:
- 1 child = 3 listeners
- 3 children = 9 listeners
- 5 children = 15 listeners
- Each listener ~100 bytes/sec bandwidth
- Home Assistant handles async efficiently

### Memory Usage

**Coordinator**:
- Stores snapshot data per child: ~5KB per child
- Children metadata: ~2KB total
- Firestore client overhead: ~10MB

**Total** (3 children):
- Coordinator data: ~15KB
- Firestore client: ~10MB
- HA entity overhead: ~50KB
- **Total**: ~10-11MB

### Startup Time

**Integration Load Sequence**:
1. Config entry setup (50ms)
2. API authentication (200-500ms)
3. Fetch children (100-300ms)
4. Setup coordinator (50ms)
5. Setup real-time listeners (300-600ms per child)
6. Forward platform setups (100ms)

**Total**: 1-3 seconds for 1-3 children

## Debugging Tips

### Integration Not Loading

**Check**:
1. Manifest.json is valid JSON
2. All required files exist
3. `__init__.py` has `async_setup_entry()`
4. Dependencies are installed
5. Home Assistant logs for errors

**Common causes**:
- Syntax errors in Python files
- Missing dependencies in manifest.json
- Invalid config flow implementation

### Entities Not Appearing

**Check**:
1. Platforms listed in PLATFORMS constant
2. `async_forward_entry_setups()` called
3. Platform `async_setup_entry()` creates entities
4. Entity `unique_id` is properly set
5. Entity added to `async_add_entities()`

**Common causes**:
- Platform not in PLATFORMS list
- Entity not added to entities list
- Duplicate unique_id

### Services Not Working

**Check**:
1. Service registered with `hass.services.async_register()`
2. Service name matches services.yaml
3. Service handler is async
4. Device selector implementation correct
5. Child UID resolution works

**Common causes**:
- Service not registered
- Typo in service name
- Device ID not found
- Child UID extraction fails

### Real-time Updates Not Working

**Check**:
1. Listeners properly setup in coordinator
2. Callback function receives updates
3. Coordinator data updated in callback
4. `async_set_updated_data()` called
5. Entity reads from coordinator

**Common causes**:
- Listener not registered
- Callback not updating coordinator
- Entity caching stale data
- Wrong document path

## Future Development Guidelines

### Adding New Platforms

1. **Create platform file**: `new_platform.py`
2. **Add to PLATFORMS**: Update `const.py`
3. **Implement entity**: Extend `CoordinatorEntity` and platform class
4. **Add device_info**: For device grouping
5. **Register in HA**: Forward setup in `__init__.py`

### Adding New Services

1. **Define in services.yaml**: With device selector
2. **Create handler**: Async function in `__init__.py`
3. **Register service**: In `async_setup_entry()`
4. **Add device action**: Update `device_action.py`
5. **Update documentation**: README.md, AGENTS.md

### Adding New Listener

1. **Create listener setup**: In coordinator
2. **Define callback**: Update coordinator data
3. **Call on setup**: In `async_setup_listeners()`
4. **Add cleanup**: In listener stop method
5. **Update entities**: To read new data

### Code Style & Conventions

**Home Assistant Standards**:
- Follow [HA development checklist](https://developers.home-assistant.io/docs/development_checklist)
- Use `async def async_*` naming for async methods
- Type hints required for all methods
- Docstrings required for classes and public methods

**Entity Naming**:
- Unique ID: `{DOMAIN}_{child_uid}_{entity_type}`
- Entity ID: `{platform}.{child_name}_{entity_type}`
- Device: One per child with `(DOMAIN, child_uid)` identifier

**Error Handling**:
```python
try:
    await hass.async_add_executor_job(api.start_sleep, child_uid)
except ValueError as err:
    _LOGGER.warning("Invalid child UID: %s", err)
except Exception as err:
    _LOGGER.error("Failed to start sleep: %s", err)
    raise
```

## Dependencies & Compatibility

### Required Dependencies

**manifest.json**:
```json
{
  "domain": "huckleberry",
  "name": "Huckleberry Baby Tracker",
  "codeowners": ["@your-github"],
  "config_flow": true,
  "dependencies": [],
  "documentation": "https://github.com/your-repo",
  "iot_class": "cloud_push",
  "requirements": ["huckleberry-api>=0.1.14"],
  "version": "0.2.7"
}
```

**Why cloud_push**:
- Real-time Firebase listeners provide instant updates
- No polling interval required
- Push notifications from Firestore via gRPC
- Latency typically < 1 second

### Home Assistant Version

**Minimum**: 2023.1+
- Uses `async_forward_entry_setups()` (replaces deprecated `async_setup_platforms`)
- Device registry integration
- Service device selectors
- Modern coordinator pattern

**Tested**: 2024.x, 2025.x

## Version Management

### Semantic Versioning

Follow [semver.org](https://semver.org/):

- **MAJOR** (2.0.0): Breaking changes
  - Entity ID changes
  - Service signature changes
  - Config flow breaking changes

- **MINOR** (1.4.0): New features, backwards compatible
  - New services
  - New entities
  - New device actions

- **PATCH** (1.4.1): Bug fixes, backwards compatible
  - Bug fixes
  - Documentation updates
  - Performance improvements

### Updating Version

1. Update `manifest.json`: `"version": "1.4.0"`
2. Update `hacs.json`: `"version": "1.4.0"`
3. Update project version: `uv version 1.4.0`
4. Commit and push changes
5. Create release: `gh release create v1.4.0 --title "v1.4.0" --notes "Release notes here"`
6. Update AGENTS.md version history
7. Update README.md with changes

## Additional Resources

### Documentation Files

- **README.md**: User installation and usage guide
- **AGENTS.md**: This file - AI agent context guide
- **services.yaml**: Service definitions for HA

### Related Projects

- **huckleberry-api**: [PyPI](https://pypi.org/project/huckleberry-api/) | [GitHub](https://github.com/your-repo/huckleberry-api)
- API library handles all Firebase operations
- Integration depends on this library

### External References

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [Home Assistant Architecture](https://developers.home-assistant.io/docs/architecture_index)
- [Config Flow](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Data Update Coordinator](https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities)
- [Device Actions](https://developers.home-assistant.io/docs/device_automation_action)

## Maintaining This Guide

**CRITICAL FOR AI AGENTS**: This document must be kept up-to-date as the living source of truth for the Home Assistant integration.

### When to Update AGENTS.md

**ALWAYS update this file when you:**
1. **Add/modify entities** - Update entity details section
2. **Add/modify services** - Update services section
3. **Add/modify device actions** - Update device actions section
4. **Change coordinator logic** - Update coordinator documentation
5. **Fix critical bugs** - Add to Common Pitfalls
6. **Change HA compatibility** - Update dependencies section
7. **Add new platforms** - Update architecture section
8. **Discover HA-specific patterns** - Add to implementation rules

### Update Checklist

- [ ] New feature/fix documented with examples
- [ ] Services section updated if applicable
- [ ] Device actions count updated if changed
- [ ] Version history updated in manifest.json
- [ ] Clear explanation of WHY it matters
- [ ] Related sections cross-referenced

**Remember**: Future AI agents and developers depend on this document for accurate HA integration context. Incomplete or incorrect information will propagate through all future work.

---

**Last Updated**: December 15, 2025
**Integration Version**: 0.2.7
**API Library Version**: 0.1.14
**Status**: Stable, feature-complete for sleep, feeding, diaper, and growth tracking
**Home Assistant Compatibility**: 2023.1+
**Test Coverage**: Automated test suite covering config flow, entities, services, and device actions
