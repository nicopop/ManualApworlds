# Template Archipelago Manual Randomizer Guide

<p align="center">
    <img alt="Archipelago Logo"
     src="https://archipelago.gg/static/static/branding/landing-logo.png"
    >
    <h1 align="center">Template</h1>
    <p align="center">v1.0.0</p>
</p>

Last-Updated 2026-09-27 (yyyy-mm-dd)

## What it this?

This Apworld is a customized template I(Nicopopxd) use when I make Manual Apworlds.  
It contains multiple Hooks that let you do more than the standard Manual template can.  
It also includes a custom client that let you use some of those additions

Bellow you can find what each hooks does in detail:

### Data.py

- `load_manifest() -> dict[str, Any]` function that let you read the content of the manifest file
- `after_load_event_file`:
  - `create_event` property for location
    - This property let you tell a location to create an event automatically linked to it (via copy_location)
    - Values type effects:
      - a bool -> false (default) create no event / true create an event named "[Event] location name"
      - a string -> an event named like that is created
        - if you include a `@` prefix, "[Event] " is added automatically before the event name
      - an object/dict -> create an event using the properties you specified
      - a list -> either a list of str or object that correspond to the 2 previous types. will create all the specified events
  - `event_visible` and `event_category`
    - let you specify that each event created for this location should have say visibility and/or category value
- `after_load_meta_file`
  - Include code that modify what's displayed on the webhost for my manual
    - adding the apworld version to the game description dynamically
    - setting the background theme to ocean
    - adding a bug_report link to the manual discord (Usually changed to be a link to the exact channel on discord)

### Helpers.py

- `before_is_category_enabled` calls a custom status system that let you turn on and off categories (see below)
- Custom `get_category_status`, `set_category_status`, `create_category_status` and `InitCategories`
  - `get_category_status(world: "ManualWorld", category_name: str)`
    - returns if the category has enabled(`true`), disabled(`False`) via `set_category_status` or none (`None`)
  - `set_category_status(world: "ManualWorld", category_name: str, status: bool)`
    - let you set the status of a category for the world
    - (is not player dependant(aka player 1 can have category X enable while for P2 its disabled))
  - `create_category_status` and `InitCategories` are both only called once per player
    - `create_category_status` creates the custom world atribute where the statuses are saved
    - `InitCategories` is where I usually do multiple set_category_status that changes based on the options value given by the player
- `before_is_location_enabled` and `before_is_item_enabled`
  - both check for a custom `remove_locations/items` option if it exists (see [Options.py](#optionspy))
  - both also call a custom `checkobject` function detailled just below
- Custom `checkobject(multiworld: MultiWorld, player: int, obj: dict[str, Any]) -> Optional[bool]`
  - Check if a Manual object as any category enabled/disabled
  1. First it check if the object has the "disabled" property set to true and if it does return False so the object is removed
  2. If there's a Goal option check if the object has the remove_if_goal property and if the goal is set to said option remove that option (unless you add a ! before the name then check if the goal is NOT this value)
  3. Check ALL the category of an item using `before_is_category_enabled`
     - if any explicitly say that a category is enabled then the item stays enabled
     - if previous does not apply check for any category that are disabled and disabled the item
     - else return None
- `before_is_event_enabled`
  - if `enabled_with_location` or `copy_location` are added to an event those location are used to check if an event is enabled
  - else give the event dict itself to `before_is_location_enabled`

### Options.py

- Custom Option Base Classes `ChoiceIsRandom`, `ToggleIsRandom`/`DefaultOnToggleIsRandom` and `RangeIsRandom`
  - They act like the base option without their `IsRandom` suffix but they keep track of if the player's value is or not randomized
    - You can do so by checking the custom `randomized` attribute that either contain the possible value from witch it was randomized or False if its not randomized
    - if you `bool(randomized)` you get `true` if its `randomized` or `false` if its not
- Custom Options Classes `RemoveItems` and `RemoveLocation`
  - those option if added in `before_options_defined` with the `remove_items` and/or `remove_locations` identifiers will let you remove any location/items from generation but not logic (see [Helpers.py](#helperspy))
    - You can exclude items/location from those option by setting their `removable` property to `false` in their respective json file
    - by default no disabled item (via the disabled property) are included
    - any location with the victory property set to true are also automaticaly excluded

### Rules.py

- Custom Rule `Event(location: str, count: int = 1) -> str`
  - Returns the location string with "[Event] " prefix added.
- Custom Rule `TODO(args: str, collected: bool = True) -> str:` and its RB equivalent
  - Return the string equivalent to the `collected` argument
  - also print the content of the args string once per type in the console
    - (first time you give it `Table` it will say `TODO for requirements: Table` in the console and in the log)
- Custom Rule `HasFromCategoryUnique(category: str, count: str) -> bool:` and its RB equivalent
  - A rule that checks if the player has at least `count` of the items in the given `category`, ignoring duplicates of the same item

### World.py

- Custom Client "Manual Client Nico's Experiment"
  - Include all the Code from the Client PR I created ([PR209](https://github.com/ManualForArchipelago/Manual/pull/209) and [PR219](https://github.com/ManualForArchipelago/Manual/pull/219))
  - AKA item description and support for UT OOL/glitch logic
- `hook_get_filler_item_name`
  - Any items added to the `FillerDummy` category can be generated as filler unless they are disabled [checked via before_is_item_enabled](#helperspy)
- `before_generate_early`
  - world.is_ut custom attribute that saves if this is a UT regen (`true`) or not (`false`)
  - write_spoiler_header override to include the version of this apworld in the first part of the spoiler file (just after the options values)
    - you can modify it here to include other info if you need
- `after_create_item`
  - add code so that you can mark an item as `deprioritized` since thats not in base Manual quiet yet
- `after_fill_slot_data`
  - You have example on how to add custom item descriptions dynamically in the slot_data
  - by dynamically I mean you can change the value that get shown based on simple logic once its set here it wont change later
