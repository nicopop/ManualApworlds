# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
from worlds.AutoWorld import World
from worlds.generic.Rules import add_rule
from typing import TYPE_CHECKING, cast, Any

from BaseClasses import MultiWorld, CollectionState, Item
from Options import OptionError
import logging

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from ..Items import ManualItem
from ..Locations import ManualLocation
from ..Helpers import remove_specific_item
from .Helpers import InitCategories

if TYPE_CHECKING:
    from .. import ManualWorld

# Raw JSON data from the Manual apworld, respectively:
#          data/game.json, data/items.json, data/locations.json, data/regions.json
#
from ..Data import game_table, item_table, location_table, region_table
from .Options import EarlyShipKey, Goal

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import is_option_enabled, is_item_enabled, get_option_value

logger = logging.getLogger()
APMiscData: dict[int|str, Any] = {}
"""
Copy of any changed world item/locations
"""
########################################################################################
## Order of method calls when the world generates:
##    1. create_regions - Creates regions and locations
##    2. create_items - Creates the item pool
##    3. set_rules - Creates rules for accessing regions and locations
##    4. generate_basic - Runs any post item pool options, like place item/category
##    5. pre_fill - Creates the victory location
##
## The create_item method is used by plando and start_inventory settings to create an item from an item name.
## The fill_slot_data method will be used to send data to the Manual client for later use, like deathlink.
########################################################################################



# Use this function to change the valid filler items to be created to replace item links or starting items.
# Default value is the `filler_item_name` from game.json
def hook_get_filler_item_name(world: World, multiworld: MultiWorld, player: int) -> str | bool:
    dummyfillers = list(world.item_name_groups.get("FillerDummy", set()).union({cast(str, world.filler_item_name)}))
    return world.random.choice(dummyfillers)

def hook_generate_early(world: "ManualWorld", multiworld: MultiWorld, player: int):
    world.OWStartItems = {}
    # Set version in yaml and log
    if not APMiscData.get('version'):
        APMiscData['version'] = world.world_version.as_simple_string()
        logger.info(f"player(s) uses {world.game} version: {APMiscData['version']}")

    world.options.game_version.value = APMiscData["version"]
# region Init Options
    APMiscData[player] = {}
    goal = world.options.goal
    rdm_base_game = world.options.randomize_base_game.value
    rdm_dlc = world.options.randomize_dlc.value
    #Options Check for impossibilities
    if not (rdm_base_game or rdm_dlc):
        raise OptionError(f"player {player} need to enable at least one of 'randomize_dlc' or 'randomize_base_game'")

    if world.options.reverse_teleporters.value:
        raise ValueError("shush for now")

    if rdm_base_game:
        if goal == Goal.option_standard: goal.value = Goal.option_eye #Dynamic Goal
    else:
        if goal == Goal.option_standard: goal.value = Goal.option_prisoner #Dynamic Goal

    if rdm_base_game and not rdm_dlc:
        if world.options.require_prisoner.value:
            raise OptionError(f"player {player} has disabled the dlc but also requires going to the end of the dlc")

        if (goal == Goal.option_prisoner or goal == Goal.option_visit_all_archive or
            goal == Goal.option_stuck_in_stranger or goal == Goal.option_stuck_in_dream):
            raise OptionError(f"player {player} set a goal for somewhere disabled by 'randomize_dlc'")

            # logger.warning(f"OW: Impossible goal for player '{multiworld.get_player_name(player)}'. Was changed to Default (Vanilla%)")

        world.options.enable_spooks.value = 1 #Set to True to skip some code later
        world.options.dlc_access_items.value = 0

    elif rdm_dlc and not rdm_base_game:
        # if world.options.shuffle_spacesuit.value:
        #     raise OptionError(f"player {player} You can't shuffle SpaceSuit when you only play the dlc")
        if world.options.dlc_access_items.value:
            world.OWStartItems["Stranger Access"] = 1
        world.OWStartItems["Signaloscope"] = 1
        world.OWStartItems["Signal > DeepSpace"] = 1
    InitCategories(world, player)
#endregion
# region local override
    # All the local items are added here since thats where you are suposed to do it according to the unit tests
    for raw_item in item_table:
        raw_item = cast(dict[str, Any], raw_item)
        name = raw_item["name"]
        if raw_item.get("local") or raw_item.get("make_local"):
            world.options.local_items.value.add(name)
            raw_item["make_local"] = raw_item.pop("local",True)
        if raw_item.get("trap"): # let trap percent decide the numbers
            raw_item["count"] = 0
#endregion
# region Ship Key logic
    # option_local_early = 0 default in items.json
    # option_local_anywhere = 1
    # option_global_early = 2
    # option_global_anywhere = 3
    # option_startswith = 4 default option value
    early_Ship = world.options.ship_key_logic.value
    shipitem = "Ship Key"
    if early_Ship == EarlyShipKey.option_startswith:
        multiworld.local_early_items[player].pop(shipitem, "")
        world.OWStartItems[shipitem] = 1
    elif early_Ship == EarlyShipKey.option_local_early:
        pass
    elif early_Ship == EarlyShipKey.option_local_anywhere:
        multiworld.local_early_items[player].pop(shipitem, "")
        world.options.local_items.value.add(shipitem)
    elif early_Ship == EarlyShipKey.option_global_early:
        multiworld.local_early_items[player].pop(shipitem, "")
        multiworld.early_items[player][shipitem] = 1
    elif early_Ship == EarlyShipKey.option_global_anywhere:
        multiworld.local_early_items[player].pop(shipitem, "")
#endregion
    pass
# Called before regions and locations are created. Not clear why you'd want this, but it's here. Victory location is included, but Victory event is not placed yet.
def before_create_regions(world: World, multiworld: MultiWorld, player: int):
    pass

# Called after regions and locations are created, in case you want to see or modify that information. Victory location is included.
def after_create_regions(world: World, multiworld: MultiWorld, player: int):
    # Use this hook to remove locations from the world
    solanum = world.options.require_solanum.value
    owlguy = world.options.require_prisoner.value
    goal = world.options.goal.value

#region Removing locations
    locations_to_be_removed = []

    # Selecting what content to remove
    #region

    if goal == Goal.option_ash_twin_project_break_spacetime:
        locations_to_be_removed.append('1 - Break Space-Time in the Ash Twin Project')

    elif goal == Goal.option_high_energy_lab_break_spacetime:
        locations_to_be_removed.append('1 - Break space time in the lab')

    elif goal == Goal.option_visit_all_archive:
        locations_to_be_removed.append('9 - In a loop visit all 3 archive without getting caught')

    elif goal == Goal.option_prisoner:

        locations_to_be_removed.append('94 - Enter the Sealed Vault in the Subterranean Lake Dream')

    #endregion

    #Removing Locations
    #region

    if len(locations_to_be_removed) > 0:
        for region in multiworld.regions:
            if region.player != player:
                continue
            for location in list(region.locations):
                if location.name in locations_to_be_removed:
                    region.locations.remove(location)

    #endregion
#endregion
    pass
# This hook allows you to access the item names & counts before the items are created. Use this to increase/decrease the amount of a specific item in the pool
# Valid item_config key/values:
# {"Item Name": 5} <- This will create qty 5 items using all the default settings
# {"Item Name": {"useful": 7}} <- This will create qty 7 items and force them to be classified as useful
# {"Item Name": {"progression": 2, "useful": 1}} <- This will create 3 items, with 2 classified as progression and 1 as useful
# {"Item Name": {0b0110: 5}} <- If you know the special flag for the item classes, you can also define non-standard options. This setup
#       will create 5 items that are the "useful trap" class
# {"Item Name": {ItemClassification.useful: 5}} <- You can also use the classification directly
def before_create_items_all(item_config: dict[str, int|dict], world: World, multiworld: MultiWorld, player: int) -> dict[str, int|dict]:
#region Personal Item counts adjustment
    rdm_base_game = world.options.randomize_base_game.value
    rdm_dlc = world.options.randomize_dlc.value
    solanum = world.options.require_solanum

    if rdm_base_game and not rdm_dlc:
        item_config["Musical Instrument"] = 5
    elif rdm_dlc and not rdm_base_game:
        if not solanum:
            item_config["Musical Instrument"] = 5
#endregion
    return item_config

# The item pool before starting items are processed, in case you want to see the raw item pool at that stage
def before_create_items_starting(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# The item pool after starting items are processed but before filler is added, in case you want to see the raw item pool at that stage
def before_create_items_filler(item_pool: list[Item], world: "ManualWorld", multiworld: MultiWorld, player: int) -> list:
    solanum = world.options.require_solanum
    owlguy = world.options.require_prisoner
    rdm_base_game = world.options.randomize_base_game.value
    rdm_dlc = world.options.randomize_dlc.value
    goal = world.options.goal
    do_spooks = world.options.enable_spooks
    DlcMainItemsRequired = world.options.dlc_access_items
#region StartItems
    StartItems = cast(dict[str, int], world.OWStartItems)

# SuitShuffle
    if not world.options.shuffle_spacesuit.value:
        StartItems["SpaceSuit"] = 1

# Reverse Teleporters:
    if world.options.reverse_teleporters.value:
        multiworld.push_precollected(world.create_item("Reverse Teleporters"))

# Early Launch Codes

    if world.options.remove_launch_codes.value:
        StartItems["Launch Codes"] = 1

# Loop item and apply as requested
    for item in list(item_pool):
        if item.player != player:
            continue
        if item.name in StartItems.keys() and world.start_inventory.get(item.name, 0) < StartItems[item.name]:
            multiworld.push_precollected(item)
            remove_specific_item(item_pool, item)
            world.start_inventory[item.name] = world.start_inventory.get(item.name, 0) + 1

#endregion
#region Place_item Override
    locations = multiworld.get_unfilled_locations(player)
    for location in locations:
        manual_loc = world.location_name_to_location.get(location.name, {})
        if manual_loc.get("place_item") or manual_loc.get("make_place_item"):
            p_items_names = manual_loc.get("place_item", manual_loc.get("make_place_item", []))
            p_items = [i for i in item_pool if i.name in p_items_names]
            if not p_items: #empty
                raise ValueError(f"location {location.name} could not have any forced placed item from this list [{p_items_names}] none could be found in item_pool")
            p_item = world.random.choice(p_items)
            location.place_locked_item(p_item)
            remove_specific_item(item_pool, p_item)
            # raw_item["make_local"] = raw_item.pop("local",True)
            if manual_loc.get("place_item"):
                manual_loc.pop("place_item")
                manual_loc["make_place_item"] = p_items_names

        elif manual_loc.get("place_item_category"):
            forbid_names: list[str] = manual_loc.get("dont_place_item", [])
            for cat in manual_loc.get("dont_place_item_category", []):
                forbid_names.extend(world.item_name_groups.get(cat, []))
            p_items_names: list[str] = []
            for cat in manual_loc["place_item_category"]:
                p_items_names.extend(world.item_name_groups.get(cat, []))

            for name in forbid_names:
                if name in p_items_names:
                    p_items_names.remove(name)

            p_items = [i for i in item_pool if i.name in p_items_names]
            if not p_items: #empty
                raise ValueError(f"location {location.name} could not have any forced placed item from this list [{p_items_names}] none could be found in item_pool")
            p_item = world.random.choice(p_items)
            location.place_locked_item(p_item)
            remove_specific_item(item_pool, p_item)
            if manual_loc.get("place_item_category"):
                manual_loc.pop("place_item_category")
                manual_loc.pop("dont_place_item_category", None)
                manual_loc.pop("dont_place_item", None)
                manual_loc["make_place_item"] = p_items_names
            pass

#endregion
#region Personal log msg
    VictoryInfoToAdd = ""
    if solanum: VictoryInfoToAdd += " + 'Seen Goat'"
    if owlguy: VictoryInfoToAdd += " + 'Seen Elk'"
    victory_message = goal.current_option_name + VictoryInfoToAdd

    message = []
    if rdm_base_game:
        message.append("Base game")
    if rdm_dlc:
        message.append("DLC")
        if len("message") == 1:
            if goal == Goal.option_eye:
                message.append("Eye")
            elif goal == Goal.option_ash_twin_project_break_spacetime:
                message.append("Ash Twin project")
            elif goal == Goal.option_high_energy_lab_break_spacetime:
                message.append("High Energy Lab")
            elif goal == Goal.option_stuck_in_stranger or goal == Goal.option_stuck_in_dream or goal == Goal.option_stuck_with_solanum:
                message.append("Adv. warp core")
            if solanum and goal != Goal.option_stuck_with_solanum:
                message.append("Solanum")

    #logger.info(message)
    contentmsg = " + ".join(message)
    location_count = len(multiworld.get_unfilled_locations(player))
    logger.info(f"{world.game}:{multiworld.get_player_name(player)} ({player}):({contentmsg}) {len(item_pool)} items | {location_count} locations | Victory: {victory_message}")
#endregion
    return item_pool

    # Some other useful hook options:

    ## Place an item at a specific location
    # location = next(l for l in multiworld.get_unfilled_locations(player=player) if l.name == "Location Name")
    # item_to_place = next(i for i in item_pool if i.name == "Item Name")
    # location.place_locked_item(item_to_place)
    # remove_specific_item(item_pool, item_to_place)

# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
def after_create_items(item_pool: list, world: World, multiworld: MultiWorld, player: int) -> list:
    return item_pool

# Called before rules for accessing regions and locations are created. Not clear why you'd want this, but it's here.
def before_set_rules(world: World, multiworld: MultiWorld, player: int):
    pass

# Called after rules for accessing regions and locations are created, in case you want to see or modify that information.
def after_set_rules(world: World, multiworld: MultiWorld, player: int):
    # Use this hook to modify the access rules for a given location
    #extra_data = load_data_file("extra.json")
    solanum = world.options.require_solanum.value
    owlguy = world.options.require_prisoner.value
    goal = world.options.goal.value

#Victory Location access rules mod
#region
    for location in multiworld.get_filled_locations(player):
        if location.address is None and location.item is not None and location.item.name == '__Victory__':
            if solanum:
                add_rule(location,
                         lambda state: state.has("[Event] 6 - Explore the Sixth Location", player))
            if owlguy and goal != Goal.option_prisoner:
                add_rule(location,
                         lambda state: state.has("[Event] 94 - Enter the Sealed Vault in the Subterranean Lake Dream", player))
#endregion

    def Example_Rule(state: CollectionState) -> bool:
        # Calculated rules take a CollectionState object and return a boolean
        # True if the player can access the location
        # CollectionState is defined in BaseClasses
        return True

    ## Common functions:
    # location = world.get_location(location_name, player)
    # location.access_rule = Example_Rule

    ## Combine rules:
    # old_rule = location.access_rule
    # location.access_rule = lambda state: old_rule(state) and Example_Rule(state)
    # OR
    # location.access_rule = lambda state: old_rule(state) or Example_Rule(state)

# The item name to create is provided before the item is created, in case you want to make changes to it
def before_create_item(item_name: str, world: World, multiworld: MultiWorld, player: int) -> str:
    return item_name

# The item that was created is provided after creation, in case you want to modify the item
def after_create_item(item: ManualItem, world: World, multiworld: MultiWorld, player: int) -> ManualItem:
    return item

# This method is run towards the end of pre-generation, before the place_item options have been handled and before AP generation occurs
def before_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This method is run at the very end of pre-generation, once the place_item options have been handled and before AP generation occurs
def after_generate_basic(world: World, multiworld: MultiWorld, player: int):
    pass

# This method is run every time an item is added to the state, can be used to modify the value of an item.
# IMPORTANT! Any changes made in this hook must be cancelled/undone in after_remove_item
def after_collect_item(world: World, state: CollectionState, Changed: bool, item: Item):
    # the following let you add to the Potato Item Value count
    # if item.name == "Cooked Potato":
    #     state.prog_items[item.player][format_state_prog_items_key(ProgItemsCat.VALUE, "Potato")] += 1
    pass

# This method is run every time an item is removed from the state, can be used to modify the value of an item.
# IMPORTANT! Any changes made in this hook must be first done in after_collect_item
def after_remove_item(world: World, state: CollectionState, Changed: bool, item: Item):
    # the following let you undo the addition to the Potato Item Value count
    # if item.name == "Cooked Potato":
    #     state.prog_items[item.player][format_state_prog_items_key(ProgItemsCat.VALUE, "Potato")] -= 1
    pass


# This is called before slot data is set and provides an empty dict ({}), in case you want to modify it before Manual does
def before_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called after slot data is set and provides the slot data at the time, in case you want to check and modify it after Manual is done with it
def after_fill_slot_data(slot_data: dict, world: World, multiworld: MultiWorld, player: int) -> dict:
    # slot_data["item_counts"] = world.item_counts[player]
    return slot_data

# This is called right at the end, in case you want to write stuff to the spoiler log
def before_write_spoiler(world: World, multiworld: MultiWorld, spoiler_handle) -> None:
    # Visualizing here shows the items too
    # from Utils import visualize_regions
    # visualize_regions(multiworld.get_region("Menu", world.player), f"{world.game}_{world.player}.puml")

    #spoiler_handle.write(f"\nIncluded in this Async: {world.game} version {APMiscData['version']}")
    pass

# This is called when you want to add information to the hint text
def before_extend_hint_information(hint_data: dict[int, dict[int, str]], world: World, multiworld: MultiWorld, player: int) -> None:

    ### Example way to use this hook:
    # if player not in hint_data:
    #     hint_data.update({player: {}})
    # for location in multiworld.get_locations(player):
    #     if not location.address:
    #         continue
    #
    #     use this section to calculate the hint string
    #
    #     hint_data[player][location.address] = hint_string

    pass

def after_extend_hint_information(hint_data: dict[int, dict[int, str]], world: World, multiworld: MultiWorld, player: int) -> None:
    pass
