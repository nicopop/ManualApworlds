from typing import Optional, Any, TYPE_CHECKING, cast
from BaseClasses import MultiWorld, Item, Location
from Options import Choice, OptionSet

if TYPE_CHECKING:
    from .. import ManualWorld

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the category, False to disable it, or None to use the default behavior
def before_is_category_enabled(multiworld: MultiWorld, player: int, category_name: str) -> Optional[bool]:
    from .Options import EvilBiomeType
    world = cast("ManualWorld", multiworld.worlds[player])
    evil_biome = cast(EvilBiomeType, world.options.evil_biome) # type: ignore
    if category_name in ["Corruption", "Corruption Hidden"] and evil_biome.value == evil_biome.option_crimson:
        return False
    elif category_name in ["Crimson", "Crimson Hidden"] and evil_biome.value == evil_biome.option_corruption:
        return False
    category_data = world.category_table.get(category_name, {})

    return category_data.get('enabled', {}).get(player, None)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the item, False to disable it, or None to use the default behavior
def before_is_item_enabled(multiworld: MultiWorld, player: int, item:  dict[str, Any], check_removed = True) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])

# region remove_items
# this let you add an OptionSet in hooks:Options.py where the player list items to be disabled
# does nothing if the Options doesn't exist
# Don't forget to either add the 'check_removed = True' to before_is_item_enabled arguments or remove it from this if
    remove_items: OptionSet | None = getattr(world.options, "remove_items", None)
    if remove_items is not None and check_removed:
        if item["name"] in remove_items.value: # type: ignore
            return False
# endregion

    return checkobject(multiworld, player, item)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the location, False to disable it, or None to use the default behavior
def before_is_location_enabled(multiworld: MultiWorld, player: int, location:  dict[str, Any], check_removed = True) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])

# region remove_locations
# this let you add an OptionSet in hooks:Options.py where the player list location to be disabled
# does nothing if the Options doesn't exist
# Don't forget to either add the 'check_removed = True' to before_is_item_enabled arguments or remove it from this if
    remove_locations: OptionSet | None = getattr(world.options, "remove_locations", None)
    if remove_locations is not None and check_removed:
        name = cast(str, location["name"])
        if name in remove_locations.value or name.rstrip(".") in remove_locations.value:
            # the . suffix let you add variant of location without having major visual difference for the player
            return False
# endregion
    return checkobject(multiworld, player, location)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the event, False to disable it, or None to use the default behavior
def before_is_event_enabled(multiworld: MultiWorld, player: int, event:  dict[str, Any]) -> Optional[bool]:
    location: dict[str, Any] = event
    linked_loc: str|None
    if (linked_loc := event.get("enabled_with_location")) is not None:
        if linked_loc: # if left empty don't track based on a location
            location = multiworld.worlds[player].location_name_to_location[linked_loc]
    elif (linked_loc := event.get("copy_location")):
        location = multiworld.worlds[player].location_name_to_location[linked_loc]
    return before_is_location_enabled(multiworld, player, location, False)

def checkobject(multiworld: MultiWorld, player: int, obj: dict[str, Any]) -> Optional[bool]:
    """Check if a Manual object as any category enabled/disabled

    Args:
        multiworld: Multiworld
        player (int): Player id
        obj (dict[str, Any]): Manual Object to test

    Returns:
        Optional[bool]: enabled or not, return None if no category are enable or disabled
    """
    world = cast("ManualWorld", multiworld.worlds[player])
    if not hasattr(world, 'categoryInit'):
        InitCategories(world, player)

    if obj.get("disabled"):
        return False

    goal: Choice | None = getattr(world.options, "goal", None)
    if goal is not None:
        if obj.get("remove_if_goal"):
            value: str = obj["remove_if_goal"]
            reverse = False
            if value.strip().startswith("!"):
                reverse = True
                value = value.lstrip("!")
            target_goal = goal.from_any(value)
            if (target_goal == goal) != reverse: return False # type: ignore

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

def InitCategories(world: "ManualWorld", player: int):
    """Mark categories as Enabled or Disabled based on options"""
    # from .Options import Goal #imported here because otherwise cause circular import

    # goal = cast(Goal, base.options.goal) # type: ignore
    # rdm_base_game = bool(base.options.randomize_base_game.value) # type: ignore
    # rdm_dlc = bool(base.options.randomize_dlc.value) # type: ignore
    # solanum = bool(base.options.require_solanum.value) # type: ignore

    # if not rdm_dlc or not base.options.dlc_access_items.value: # type: ignore
    #     set_category_status(base, player, 'DLC - Reduced Knowledge', False)

    # set_category_status(base, player, 'Base Game', rdm_base_game)
    # set_category_status(base, player, 'DLC - Eye', rdm_dlc)

    # if rdm_dlc and not rdm_base_game:
    #     if solanum:
    #         set_category_status(base, player, 'required for solanum', True)

    #     if goal == goal.alias_vanilla:
    #         set_category_status(base, player, 'Goal Eye', True)
    #         set_category_status(base, player, 'required for warpdrive', True)
    #     elif goal == goal.alias_ash_twin_project_break_spacetime:
    #         set_category_status(base, player, 'required for warpdrive', True)
    #     # elif goal == Goal.alias_high_energy_lab_break_spacetime:
    #     elif goal == goal.alias_stuck_with_solanum:
    #         set_category_status(base, player, 'required for warpdrive', True)
    #         set_category_status(base, player, 'required for solanum', True)
    #     elif (goal == goal.alias_stuck_in_stranger or goal == goal.alias_stuck_in_dream):
    #         set_category_status(base, player, 'required for warpdrive', True)
    world.categoryInit = True # type: ignore

def set_category_status(world: "ManualWorld", player: int, category_name: str, status: bool):
    if world.category_table.get(category_name, {}):
        if not world.category_table[category_name].get('enabled', {}):
            world.category_table[category_name]['enabled'] = {}
        world.category_table[category_name]['enabled'][player] = bool(status)
