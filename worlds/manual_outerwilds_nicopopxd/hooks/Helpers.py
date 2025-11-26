from typing import Optional, Any
from BaseClasses import MultiWorld, Item, Location
from worlds.AutoWorld import World


# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the category, False to disable it, or None to use the default behavior
def before_is_category_enabled(multiworld: MultiWorld, player: int, category_name: str) -> Optional[bool]:
    world = multiworld.worlds.get(player)
    category_data = world.category_table.get(category_name, {})

    return category_data.get('enabled', {}).get(player, None)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the item, False to disable it, or None to use the default behavior
def before_is_item_enabled(multiworld: MultiWorld, player: int, item:  dict[str, Any]) -> Optional[bool]:
    if "DLC - Reduced Knowledge" in item.get('category', []):
        world = multiworld.worlds[player]
        if not world.options.randomize_dlc.value:
            return False
        return bool(world.options.dlc_access_items.value)
    return checkobject(multiworld, player, item)

# Use this if you want to override the default behavior of is_option_enabled
# Return True to enable the location, False to disable it, or None to use the default behavior
def before_is_location_enabled(multiworld: MultiWorld, player: int, location:  dict[str, Any]) -> Optional[bool]:
    if "do_place_item_category" in location.get("category", []) or "no_place_item_category" in location.get("category", []):
        world = multiworld.worlds[player]
        if not world.options.randomize_base_game.value:
             if location.get("region", "") == "Ship":
                 return "no_place_item_category" in location.get("category", [])
    return checkobject(multiworld, player, location)

def checkobject(multiworld: MultiWorld, player: int, obj: object) -> Optional[bool]:
    """Check if a Manual object as any category enabled/disabled

    Args:
        multiworld: Multiworld
        player (int): Player id
        obj (object): Manual Object to test

    Returns:
        Optional[bool]: enabled or not,
        return None if no category are enable or disabled
    """
    world = multiworld.worlds.get(player)
    if world is not None and not hasattr(world, 'categoryInit'):
        InitCategories(world, player)

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

def InitCategories(base: World, player: int):
    """Mark categories as Enabled or Disabled based on options"""
    from .Options import Goal #imported here because otherwise cause circular import

    goal = base.options.goal.value
    rdm_base_game = bool(base.options.randomize_base_game.value)
    rdm_dlc = bool(base.options.randomize_dlc.value)
    solanum = bool(base.options.require_solanum.value)

    if not rdm_dlc or not base.options.dlc_access_items.value:
        set_category_status(base, player, 'DLC - Reduced Knowledge', False)

    set_category_status(base, player, 'Base Game', rdm_base_game)
    set_category_status(base, player, 'DLC - Eye', rdm_dlc)

    if rdm_dlc and not rdm_base_game: # content == RandomContent.option_dlc:
        if solanum:
            set_category_status(base, player, 'require_solanum', True)

        if goal == Goal.option_eye:
            set_category_status(base, player, 'Win_Eye', True)
            set_category_status(base, player, 'need_warpdrive', True)
        elif goal == Goal.option_ash_twin_project_break_spacetime:
            set_category_status(base, player, 'need_warpdrive', True)
            set_category_status(base, player, 'Win_ATP_break_spacetime', True)
        elif goal == Goal.option_high_energy_lab_break_spacetime:
            set_category_status(base, player, 'need_warpdrive', True)
            set_category_status(base, player, 'Win_HEL_break_spacetime', True)
        elif goal == Goal.option_stuck_with_solanum:
            set_category_status(base, player, 'need_warpdrive', True)
            set_category_status(base, player, 'require_solanum', True)
            set_category_status(base, player, 'Win_solanum', True)
        elif (goal == Goal.option_stuck_in_stranger or goal == Goal.option_stuck_in_dream):
            set_category_status(base, player, 'need_warpdrive', True)
    base.categoryInit = True

def set_category_status(world, player: int, category_name: str, status: bool):
    if world.category_table.get(category_name, {}):
        if not world.category_table[category_name].get('enabled', {}):
            world.category_table[category_name]['enabled'] = {}
        world.category_table[category_name]['enabled'][player] = bool(status)
