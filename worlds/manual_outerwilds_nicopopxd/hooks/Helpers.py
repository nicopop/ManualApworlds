from typing import Optional, cast, Any, TYPE_CHECKING
from BaseClasses import MultiWorld, Item, Location

if TYPE_CHECKING:
    from .. import ManualWorld

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the category, False to disable it, or None to use the default behavior
def before_is_category_enabled(multiworld: MultiWorld, player: int, category_name: str) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])
    category_data = world.category_table.get(category_name, {})

    return category_data.get('enabled', {}).get(player, None)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the item, False to disable it, or None to use the default behavior
def before_is_item_enabled(multiworld: MultiWorld, player: int, item:  dict[str, Any]) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])
    if item["name"] in world.options.remove_items.value: # type: ignore
        return False
    if "DLC - Reduced Knowledge" in item.get('category', []):
        if not world.options.randomize_dlc.value: # type: ignore
            return False
        return bool(world.options.dlc_access_items.value) # type: ignore

    return checkobject(multiworld, player, item)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the location, False to disable it, or None to use the default behavior
def before_is_location_enabled(multiworld: MultiWorld, player: int, location:  dict[str, Any], check_removed = True) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])
    name = cast(str, location["name"])
    if check_removed and (name in world.options.remove_locations.value or name.rstrip(".") in world.options.remove_locations.value): # type: ignore
        return False
    if "do_place_item_category" in location.get("category", []) or "no_place_item_category" in location.get("category", []):
        if not world.options.randomize_base_game.value: # type: ignore
             if location.get("region", "") == "Ship":
                 return "no_place_item_category" in location.get("category", [])
    elif "DLC - Spooky" in location.get("category", []):
        if not world.options.enable_spooks: # type: ignore
            return False

    return checkobject(multiworld, player, location)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the event, False to disable it, or None to use the default behavior
def before_is_event_enabled(multiworld: MultiWorld, player: int, event:  dict[str, Any]) -> Optional[bool]:
    location = event
    if event.get("copy_location"):
        location =  multiworld.worlds[player].location_name_to_location[event.get("copy_location")]
    return before_is_location_enabled(multiworld, player, location, False)

def checkobject(multiworld: MultiWorld, player: int, obj: dict[str, Any]) -> Optional[bool]:
    """Check if a Manual object as any category enabled/disabled

    Args:
        multiworld: Multiworld
        player (int): Player id
        obj (dict[str, Any]): Manual Object to test

    Returns:
        Optional[bool]: enabled or not,
        return None if no category are enable or disabled
    """
    world = cast("ManualWorld", multiworld.worlds[player])
    if world is not None and not hasattr(world, 'categoryInit'):
        InitCategories(world, player)

    if obj.get("disabled") == True:
        return False

    if obj.get("remove_if_goal"):
        value: str = obj["remove_if_goal"]
        reverse = False
        if value.strip().startswith("!"):
            reverse = True
            value = value.lstrip("!")
        target_goal = world.options.goal.from_any(value) # type: ignore
        if (target_goal == world.options.goal) != reverse: return False # type: ignore

    resultYes = False
    resultNo = False
    categories = obj.get('category', [])
    for category in categories:
        result = before_is_category_enabled(multiworld, player, category)
        if result is not None:
            if result:
                resultYes = True
                break
            else:
                resultNo = True
    if resultYes:
        return True
    elif resultNo:
        return False
    return None

def InitCategories(base: "ManualWorld", player: int):
    """Mark categories as Enabled or Disabled based on options"""
    from .Options import Goal #imported here because otherwise cause circular import

    goal = cast(Goal, base.options.goal) # type: ignore
    rdm_base_game = bool(base.options.randomize_base_game.value) # type: ignore
    rdm_dlc = bool(base.options.randomize_dlc.value) # type: ignore
    solanum = bool(base.options.require_solanum.value) # type: ignore

    if not rdm_dlc or not base.options.dlc_access_items.value: # type: ignore
        set_category_status(base, player, 'DLC - Reduced Knowledge', False)

    set_category_status(base, player, 'Base Game', rdm_base_game)
    set_category_status(base, player, 'DLC - Eye', rdm_dlc)

    if rdm_dlc and not rdm_base_game:
        if solanum:
            set_category_status(base, player, 'required for solanum', True)

        if goal == goal.alias_vanilla:
            set_category_status(base, player, 'Goal Eye', True)
            set_category_status(base, player, 'required for warpdrive', True)
        elif goal == goal.alias_ash_twin_project_break_spacetime:
            set_category_status(base, player, 'required for warpdrive', True)
        # elif goal == Goal.alias_high_energy_lab_break_spacetime:
        elif goal == goal.alias_stuck_with_solanum:
            set_category_status(base, player, 'required for warpdrive', True)
            set_category_status(base, player, 'required for solanum', True)
        elif (goal == goal.alias_stuck_in_stranger or goal == goal.alias_stuck_in_dream):
            set_category_status(base, player, 'required for warpdrive', True)
    base.categoryInit = True # type: ignore

def set_category_status(world, player: int, category_name: str, status: bool):
    if world.category_table.get(category_name, {}):
        if not world.category_table[category_name].get('enabled', {}):
            world.category_table[category_name]['enabled'] = {}
        world.category_table[category_name]['enabled'][player] = bool(status)
