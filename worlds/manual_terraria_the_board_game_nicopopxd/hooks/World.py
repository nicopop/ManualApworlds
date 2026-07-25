# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
from worlds.AutoWorld import World
from typing import TYPE_CHECKING, cast, Any, Callable

from BaseClasses import MultiWorld, CollectionState, Item, Location, ItemClassification
from Options import OptionError
import logging

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from ..Items import ManualItem
from ..Locations import ManualLocation
from .Helpers import InitCategories

if TYPE_CHECKING:
    from .. import ManualWorld

# Raw JSON data from the Manual apworld, respectively:
#          data/game.json, data/items.json, data/locations.json, data/regions.json
#
from ..Data import game_table, item_table, location_table, region_table
from .Options import CorruptionType, BiomeRdmSeed

# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from ..Helpers import remove_specific_item, is_item_enabled, is_location_name_enabled
from random import Random

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

# region Custom Client
from worlds.LauncherComponents import Component, SuffixIdentifier, components, Type, launch, icon_paths
def launch_client(*args):
    import CommonClient
    from ..ManualClient import launch as Main

    if CommonClient.gui_enabled:
        launch(Main, name="Manual client", args=args)
    else:
        Main(*args)

class VersionedComponent(Component):
    def __init__(self, display_name: str, script_name: str|None = None, func: Callable|None = None, version: int = 0, file_identifier: Callable[[str], bool]|None = None, icon: str = ""):
        super().__init__(display_name=display_name, script_name=script_name, func=func, component_type=Type.CLIENT, file_identifier=file_identifier, icon=icon)
        self.version = version

def add_client_to_launcher() -> None:
    import Utils
    version = 2026_04_13 # YYYYMMDD
    found = False

    if "manual" not in icon_paths:
        icon_paths["manual"] = Utils.user_path('data', 'manual.png')

    for c in components:
        if c.display_name == "Manual Client Nico's Experiment":
            found = True
            if getattr(c, "version", 0) < version:
                c.version = version # type: ignore
                c.func = launch_client
                c.icon = "manual"

    if not found:
        components.append(VersionedComponent("Manual Client Nico's Experiment", "ManualClient", func=launch_client, version=version, file_identifier=SuffixIdentifier('.apmanual'), icon="manual"))
add_client_to_launcher()
# endregion
# Use this function to change the valid filler items to be created to replace item links or starting items.
# Default value is the `filler_item_name` from game.json
def hook_get_filler_item_name(world: "ManualWorld", multiworld: MultiWorld, player: int) -> str | bool:
    dummyfillers = list(world.item_name_groups.get("FillerDummy", set()))
    dummyfillers = [i for i in dummyfillers if is_item_enabled(multiworld, player, world.item_name_to_item[i])]
    if not dummyfillers:
        return world.filler_item_name
    return world.random.choice(dummyfillers)

def before_generate_early(world: "ManualWorld", multiworld: MultiWorld, player: int):
    """
    This is the earliest hook called during generation, before anything else is done.
    Use it to check or modify incompatible options, or to set up variables for later use.
    """
    world.options.game_version.value = world.world_version.as_simple_string() # type: ignore
    # ? maybe remove the game_version option and move to before_write_spoiler
# region Init Options
    weird_type = cast(CorruptionType, world.options.weird_biome) # type: ignore
    biome_seed = cast(BiomeRdmSeed, world.options.biome_seed) # type: ignore

    if biome_seed.value != biome_seed.option_default:
        world.biome_random = Random(biome_seed.value) # type: ignore
    else:
        world.biome_random = world.random # type: ignore

    # running the random choice here either way so the seed can stay on the same step
    # TODO Check for UT and skip all random
    weird_type.value = world.biome_random.choice(weird_type.get_randomized_values())

    # ? maybe do the entrance order here and adapt later


# endregion
    pass
# Called before regions and locations are created. Not clear why you'd want this, but it's here. Victory location is included, but Victory event is not placed yet.
def before_create_regions(world: "ManualWorld", multiworld: MultiWorld, player: int):
    pass

# Called after regions and locations are created, in case you want to see or modify that information. Victory location is included.
def after_create_regions(world: "ManualWorld", multiworld: MultiWorld, player: int):
    pass
# This hook allows you to access the item names & counts before the items are created. Use this to increase/decrease the amount of a specific item in the pool
# Valid item_config key/values:
# {"Item Name": 5} <- This will create qty 5 items using all the default settings
# {"Item Name": {"useful": 7}} <- This will create qty 7 items and force them to be classified as useful
# {"Item Name": {"progression": 2, "useful": 1}} <- This will create 3 items, with 2 classified as progression and 1 as useful
# {"Item Name": {0b0110: 5}} <- If you know the special flag for the item classes, you can also define non-standard options. This setup
#       will create 5 items that are the "useful trap" class
# {"Item Name": {ItemClassification.useful: 5}} <- You can also use the classification directly
def before_create_items_all(item_config: dict[str, int|dict], world: "ManualWorld", multiworld: MultiWorld, player: int) -> dict[str, int|dict]:
    return item_config

# The item pool before place_item(_category) are processed, in case you want to see the raw item pool at that stage
def before_create_items_place_items(item_pool: list, world: "ManualWorld", multiworld: MultiWorld, player: int) -> list:
    return item_pool

# The item pool before starting items are processed, in case you want to see the raw item pool at that stage
def before_create_items_starting(item_pool: list, world: "ManualWorld", multiworld: MultiWorld, player: int) -> list:
    return item_pool

# The item pool after starting items are processed but before filler is added, in case you want to see the raw item pool at that stage
def before_create_items_filler(item_pool: list[Item], world: "ManualWorld", multiworld: MultiWorld, player: int) -> list:
    # region Biome Gen
    # AKA jank entrance rando
    _random = cast(Random, world.biome_random)

    tokens: list[Item] = []
    ocean_tokens: dict[str, Item] = {}
    for item in item_pool:
        if item.name in world.item_name_groups["Biome Token"]:
            tokens.append(item)
        elif item.name in world.item_name_groups["Ocean Token"]:
            ocean_tokens[item.name.removesuffix(" Ocean Biome")] = item

    discovery_locs: dict[str, Location] = {}
    for loc_name in world.location_name_groups["Discover"]:
        if is_location_name_enabled(multiworld, player, loc_name):
            discovery_locs[loc_name] = world.get_location(loc_name)

    _random.shuffle(tokens)

    #         ocean, biome,  biome,  forest l, forest r, biome, biome, ocean
    # biome:  ocean, desert, jungle,       forest,       snow,  corup, ocean
    #                   0       1            2              3      4
    # tokens: none,  ocean,  desert,    jungle + snow,   corup, ocean, none
    #                          0          1       2       3
    biomes = [i.name.removesuffix(" Biome") for i in tokens]
    biomes.insert(2, "Forest")

    for index, biome in enumerate(biomes):
        left = index < 3
        name = f"{biome} Discover Biome"
        if biome == "Forest":
            # right forest done here and let the code below do left
            location = discovery_locs.pop(name + " Right")
            token = tokens[index]

            location.place_locked_item(token)
            remove_specific_item(item_pool, token)

            name += " Left"
        location = discovery_locs.pop(name)

        token_idx = index - 1 if left else index
        token = tokens[token_idx] if -1 < token_idx < len(tokens)\
            else ocean_tokens["Left" if left else "Right"]

        # TODO save `name` to token description or maybe just `biome`
        logging.debug(f"({world.game}) {world.player_name}({player}): {name} -> {token.name}")
        location.place_locked_item(token)
        remove_specific_item(item_pool, token)
    # ! there's probably a more inteligent way to do this but I don't know right now
    logging.info(f"({world.game}) biome layout for player {world.player_name}({player}): {', '.join(biomes)}")
    # endregion
    return item_pool

    # Some other useful hook options:

    ## Place an item at a specific location
    # location = next(l for l in multiworld.get_unfilled_locations(player=player) if l.name == "Location Name")
    # item_to_place = next(i for i in item_pool if i.name == "Item Name")
    # location.place_locked_item(item_to_place)
    # remove_specific_item(item_pool, item_to_place)

# The complete item pool prior to being set for generation is provided here, in case you want to make changes to it
def after_create_items(item_pool: list, world: "ManualWorld", multiworld: MultiWorld, player: int) -> list:
    return item_pool

# Called before rules for accessing regions and locations are created. Not clear why you'd want this, but it's here.
def before_set_rules(world: "ManualWorld", multiworld: MultiWorld, player: int):
    pass

# Called after rules for accessing regions and locations are created, in case you want to see or modify that information.
def after_set_rules(world: "ManualWorld", multiworld: MultiWorld, player: int):
    # Use this hook to modify the access rules for a given location
    #extra_data = load_data_file("extra.json")
    # solanum = world.options.require_solanum.value
    # owlguy = world.options.require_prisoner.value
    # goal = world.options.goal.value

#Victory Location access rules mod
#region
    # for location in multiworld.get_filled_locations(player):
    #     if location.address is None and location.item is not None:
    #         if location.item.name == '__Victory__':
    #             if solanum:
    #                 add_rule(location,
    #                         lambda state: state.has("[Event] 6 - Explore the Sixth Location", player))
    #             if owlguy and goal != Goal.alias_prisoner:
    #                 add_rule(location,
    #                         lambda state: state.has("[Event] 94 - Enter the Sealed Vault in the Subterranean Lake Dream", player))
            # elif location.name.startswith("[Event] "):
            #     name = location.name.removeprefix("[Event] ")
            #     original = multiworld.get_location(name, player)
            #     add_rule(location, lambda state: original.access_rule(state))
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
def before_create_item(item_name: str, world: "ManualWorld", multiworld: MultiWorld, player: int) -> str:
    return item_name

# The item that was created is provided after creation, in case you want to modify the item
def after_create_item(item: ManualItem, world: "ManualWorld", multiworld: MultiWorld, player: int) -> ManualItem:
    return item

# This method is run towards the end of pre-generation, before the place_item options have been handled and before AP generation occurs
def before_generate_basic(world: "ManualWorld", multiworld: MultiWorld, player: int):
    pass

# This method is run at the very end of pre-generation, once the place_item options have been handled and before AP generation occurs
def after_generate_basic(world: "ManualWorld", multiworld: MultiWorld, player: int):
    pass

# This method is run every time an item is added to the state, can be used to modify the value of an item.
# IMPORTANT! Any changes made in this hook must be cancelled/undone in after_remove_item
def after_collect_item(world: "ManualWorld", state: CollectionState, Changed: bool, item: Item):
    # the following let you add to the Potato Item Value count
    # if item.name == "Cooked Potato":
    #     state.prog_items[item.player][format_state_prog_items_key(ProgItemsCat.VALUE, "Potato")] += 1
    pass

# This method is run every time an item is removed from the state, can be used to modify the value of an item.
# IMPORTANT! Any changes made in this hook must be first done in after_collect_item
def after_remove_item(world: "ManualWorld", state: CollectionState, Changed: bool, item: Item):
    # the following let you undo the addition to the Potato Item Value count
    # if item.name == "Cooked Potato":
    #     state.prog_items[item.player][format_state_prog_items_key(ProgItemsCat.VALUE, "Potato")] -= 1
    pass


# This is called before slot data is set and provides an empty dict ({}), in case you want to modify it before Manual does
def before_fill_slot_data(slot_data: dict, world: "ManualWorld", multiworld: MultiWorld, player: int) -> dict:
    return slot_data

# This is called after slot data is set and provides the slot data at the time, in case you want to check and modify it after Manual is done with it
def after_fill_slot_data(slot_data: dict, world: "ManualWorld", multiworld: MultiWorld, player: int) -> dict:
    # victory_name: str = world.victory_names[world.options.goal.value]
    # Manual_victory = world.location_name_to_location[victory_name]
    # needed: list[str] = []
    # if world.options.require_solanum.value:
    #     needed.append("Solanum")
    # if world.options.require_prisoner.value and world.options.goal.value != Goal.alias_prisoner:
    #     needed.append("the Prisoner")
    # if needed:
    #     base_alias = Manual_victory.get('alias', None)
    #     if base_alias is not None:
    #         alias = f"{base_alias} + {' and '.join(needed)}"
    #     else:
    #         alias = f"{' and '.join(needed)}"
    #     if "location_id_to_alias" not in slot_data.keys():
    #         slot_data["location_id_to_alias"] = {}
    #     slot_data["location_id_to_alias"][Manual_victory["id"]] = alias
    return slot_data

# This is called right at the end, in case you want to write stuff to the spoiler log
def before_write_spoiler(world: "ManualWorld", multiworld: MultiWorld, spoiler_handle) -> None:
    # Visualizing here shows the items too
    # from Utils import visualize_regions
    # visualize_regions(multiworld.get_region("Menu", world.player), f"{world.game}_{world.player}.puml")

    #spoiler_handle.write(f"\nIncluded in this Async: {world.game} version {APMiscData['version']}")
    pass

# This is called when you want to add information to the hint text
def before_extend_hint_information(hint_data: dict[int, dict[int, str]], world: "ManualWorld", multiworld: MultiWorld, player: int) -> None:

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

def after_extend_hint_information(hint_data: dict[int, dict[int, str]], world: "ManualWorld", multiworld: MultiWorld, player: int) -> None:
    pass

def hook_interpret_slot_data(world: "ManualWorld", player: int, slot_data: dict[str, Any]) -> dict[str, Any]:
    """
        Called when Universal Tracker wants to perform a fake generation
        Use this if you want to use or modify the slot_data for passed into re_gen_passthrough
    """
    return slot_data
