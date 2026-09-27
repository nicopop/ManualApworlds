from typing import Optional, Any, TYPE_CHECKING, cast
from BaseClasses import MultiWorld, Item, Location
from Options import Choice, OptionSet

if TYPE_CHECKING:
    from .. import ManualWorld

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the category, False to disable it, or None to use the default behavior
def before_is_category_enabled(multiworld: MultiWorld, player: int, category_name: str) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])

    return get_category_status(world, category_name)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the item, False to disable it, or None to use the default behavior
def before_is_item_enabled(multiworld: MultiWorld, player: int, item:  dict[str, Any], check_removed = True) -> Optional[bool]:
    world = cast("ManualWorld", multiworld.worlds[player])
    remove_items: OptionSet | None = getattr(world.options, "remove_items", None)
    if remove_items is not None and check_removed:
        if item["name"] in remove_items.value:
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
    remove_locations: OptionSet | None = getattr(world.options, "remove_locations", None)
    if remove_locations is not None and check_removed:
        if name in remove_locations.value or name.rstrip(".") in remove_locations.value:
            # the . suffix let you add variant of location without having major visual difference for the player
            return False
    if "do_place_item_category" in location.get("category", []) or "no_place_item_category" in location.get("category", []):
        if not world.options.randomize_base_game.value: # type: ignore
             if location.get("region", "") == "Ship":
                 return "no_place_item_category" in location.get("category", [])
    elif "DLC - Spooky" in location.get("category", []):
        if not getattr(world.options, "enable_spooks"): # type: ignore
            return False

    return checkobject(multiworld, player, location)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the event, False to disable it, or None to use the default behavior
def before_is_event_enabled(multiworld: MultiWorld, player: int, event:  dict[str, Any]) -> Optional[bool]:
    location: dict[str, Any] = event
# region Event enabled?
# In this Template Events are linked by default with the copied location unless you changes it
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
            if (target_goal == goal) != reverse: return False

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

def InitCategories(world: "ManualWorld"):
    """Mark categories as Enabled or Disabled based on options"""
    from .Options import Goal #imported here because otherwise cause circular import

    options = world.options
    goal = cast(Goal, getattr(options, "goal"))
    rdm_base_game = bool(getattr(options, "randomize_base_game").value)
    rdm_dlc = bool(getattr(options, "randomize_dlc").value)
    solanum = bool(getattr(options, "require_solanum").value)

    if not rdm_dlc or not bool(getattr(options, "dlc_access_items").value):
        set_category_status(world, 'DLC - Reduced Knowledge', False)

    set_category_status(world, 'Base Game', rdm_base_game)
    set_category_status(world, 'DLC - Eye', rdm_dlc)

    if rdm_dlc and not rdm_base_game:
        if solanum:
            set_category_status(world, 'required for solanum', True)

        if goal == goal.alias_vanilla:
            set_category_status(world, 'Goal Eye', True)
            set_category_status(world, 'required for warpdrive', True)
        elif goal == goal.alias_ash_twin_project_break_spacetime:
            set_category_status(world, 'required for warpdrive', True)
        # elif goal == Goal.alias_high_energy_lab_break_spacetime:
        elif goal == goal.alias_stuck_with_solanum:
            set_category_status(world, 'required for warpdrive', True)
            set_category_status(world, 'required for solanum', True)
        elif (goal == goal.alias_stuck_in_stranger or goal == goal.alias_stuck_in_dream):
            set_category_status(world, 'required for warpdrive', True)


def create_category_status(world: "ManualWorld"):
    world.NicoCategoryStatus = dict[str, bool]() # type: ignore

def set_category_status(world: "ManualWorld", category_name: str, status: bool):
    if getattr(world, "NicoCategoryStatus", None) is None:
        create_category_status(world)

    world.NicoCategoryStatus[category_name] = status

def get_category_status(world: "ManualWorld", category_name: str) -> bool | None:
    categoryStatus: dict[str, bool] | None = getattr(world, "NicoCategoryStatus", None)
    if categoryStatus is None:
        InitCategories(world)
        return get_category_status(world, category_name)

    return categoryStatus.get(category_name, None)