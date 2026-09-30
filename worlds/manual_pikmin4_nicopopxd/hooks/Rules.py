from typing import Optional, TYPE_CHECKING, cast, Any
from typing_extensions import override
from rule_builder.rules import Rule
from worlds.AutoWorld import World
from ..Helpers import clamp, get_items_with_value, is_item_name_enabled, format_state_prog_items_key
from ..Game import game_name
from BaseClasses import MultiWorld, CollectionState

import dataclasses
import logging
from Utils import version_tuple
use_rulebuilder = version_tuple >= (0, 6, 7)

if TYPE_CHECKING:
    from .. import ManualWorld

def Build() -> str:
    return "|Russ|"

def Night() -> str:
    return "|Yonny|"

def ElectricalGate(st:bool = False) -> str:
    if st: # TODO check if other equipment work too
        return "{Pikmin(ST Yellow)}"

    return "{Pikmin(Yellow)} or (|Pup Anti-Electrifier|)\
        or (|Anti-Electrifier| and {TODO(Melee Setting)})"

def IceGate() -> str:
    return "{Pikmin(Ice)} or (|Pup Thermal Defense|)\
        or (|Thermal Defense| and {TODO(Melee Setting)})"

def FreezeWater(count: int, short_duration: bool = False) -> str:
    if short_duration:
        return f"{{Pikmin(Ice, {count})}} or {{Bombs(Ice)}}"
    else:
        return f"{{Pikmin(Ice, {count})}}"

def FireFloor() -> str:
    return "{Pikmin(Red)} or (|Pup Scorch Guard|)\
        or (|Scorch Guard| and {TODO(Melee Setting)})"

def PoisonFloor() -> str:
    return "{Pikmin(White)} or (|Pup Sniff Saver|)\
        or {TODO(Melee Setting, False)}"

def Bombs(bomb_type: str = "Normal") -> str:
    bomb_type = bomb_type.lower()
    requires = ""
    if bomb_type == "normal":
        requires = "({EventValue(Sparklium:3000)} or |NGP|) and |Bomb Rocks|"
    if bomb_type == "ice":
        requires = "({EventValue(Sparklium:1500)} or |NGP|) and |Ice Blasts|"
    elif bomb_type == "mine":
        requires = "({EventValue(Sparklium:1500)} or |NGP|) and |Mines|"
    elif bomb_type == "track":
        requires = "({EventValue(Sparklium:7500)} or |NGP|) and |Trackonators|"
    return "|Russ| and " + requires

def CanLiftST(count: int, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    Real_pikmins = world.event_name_groups["ST Pikmins Carry"]
    max_pikmin_count = ceil(count/10)
    return state.has_from_list(Real_pikmins, player, max_pikmin_count)

def CanLiftOverWater(FreezeCount: int, Weight: int, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    Real_pikmins = set(world.event_name_groups["Pikmins Carry"])
    without_ice = set(Real_pikmins)
    without_ice.remove("Ice Real")
    item_freeze_count = ceil(FreezeCount/10)
    item_weight_count = ceil(Weight/10)
    # Frozen
    if state.has("Ice Real", player, item_freeze_count + item_weight_count):
        return True
    elif state.has("Ice Real", player, item_freeze_count) and CanLift(Weight, state, world, player, "Ice")\
        and state.has("Flarlic", player, item_freeze_count + item_weight_count):
        return True
    # Other Pikmins
    elif state.has_any_count({"Blue Real": item_weight_count, "Pink Real": item_weight_count}, player):
        return True
    return False

def CanLift(count: int, state: CollectionState, world: "ManualWorld", player: int, excluded_colors: str = "") -> bool:
    Real_pikmins = set(world.event_name_groups["Pikmins Carry"])

    excluded = excluded_colors.split(";")
    for color in excluded:
        Real_pikmins.remove(f"{color} Real")

    max_pikmin_count = ceil(count/10)
    rule: bool
    if count <= 100:
        rule = state.has_from_list(Real_pikmins, player, count=max_pikmin_count) or state.has("Purple Real", player, max_pikmin_count)
        if rule:
            return True
        for i in range(max_pikmin_count-1):
            right = state.has("Purple Real", player, i) and state.has_from_list(Real_pikmins, player, count=max_pikmin_count-i)
            if right:
                return True
        return False
    else:
        extra = count - 100 # to find minimum count of purple 101-100 = 1
        min_purple_count = ceil(extra/100) # ceil(101/100) = 1
        max_purple_count = ceil(count/100) # 2
        if state.has("Purple Real", player, max_purple_count):
            return True
        for i in range(min_purple_count, max_purple_count):
            new_max_pikmin_count = min(ceil((count - i * 100) / 10), 0) # ceil((101 - 2*100)/ 10) = ceil(-1 / 10) = -1
            if state.has("Purple Real", player, i) and (not new_max_pikmin_count or state.has_from_list(Real_pikmins, player, count=new_max_pikmin_count)):
                return True
        return False

from math import ceil
def Pikmin(state: CollectionState, player: int, color: str, count: int = 1) -> bool:
    if color.lower() == "purple":
        item_count = ceil(count/100)
    else:
        item_count = ceil(count/10)
    flarlic_count = max(item_count - 2, 0)
    flarlic = "Flarlic"
    if color.startswith("ST "):
        flarlic = "ST Flarlic"
    return state.has(f"{color} Pikmins", player, item_count) and state.has(flarlic, player, flarlic_count) \
        and (state.has(f"{color} Onion", player) or state.has(f"{color} Pikmin Source", player))

def Event(location: str, count: int = 1) -> str:
    event_name = f"|[Event] {location.strip()}:{count}|"
    return event_name

knownTODO = set()

def TODO(args: str, collected: bool = True) -> str:
    global knownTODO
    if args.lower().strip() not in knownTODO:
        logging.warning(f"TODO for requirements: {args}")
        knownTODO.add(args.lower().strip())
    return "1" if collected else "0"

def EventValue(state: CollectionState, player: int, valueCount: str):
    """When passed a string with this format: 'valueName:int',
    this function will check if the player has collect at least 'int' valueName worth of items\n
    eg. {ItemValue(Coins:12)} will check if the player has collect at least 12 coins worth of items
    """

    args: list[str] = valueCount.split(":")
    if not len(args) == 2 or not args[1].isnumeric():
        raise Exception(f"EventValue needs a number after : so it looks something like 'EventValue({args[0]}:12)'")
    value_name = format_state_prog_items_key("EVENT_VALUE", args[0])
    requested_count = int(args[1].strip())
    return state.has(value_name, player, requested_count)


# A rule that checks if the player has at least count of the given items, ignoring duplicates of the same item
def HasFromCategoryUnique(category: str, count: str, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    requested_count = int(count.strip())
    return state.has_from_list_unique(world.item_and_event_name_groups[category], player, requested_count)

# def GoalObjectives(state: CollectionState, world: "ManualWorld", player: int,) -> bool:
#     from .Options import ObjectivesTypesForGoal
#     objectives = cast(ObjectivesTypesForGoal, world.options.goal_objectives) # type: ignore
#     requested_count = objectives.value
#     return HasFromCategoryUnique("Objectives Final", str(requested_count), state=state, world=world, player=player)

if use_rulebuilder:
    from rule_builder.rules import HasFromListUnique, Rule, True_, False_, Has, HasAnyCount, HasFromList, Or, And

    @dataclasses.dataclass()
    class PikminRule(Rule["ManualWorld"], game=game_name):
        color: str
        count: int = 1
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            color = self.color
            count = self.count
            if self.color.lower() == "purple":
                item_count = ceil(count/100)
            else:
                item_count = ceil(count/10)
            flarlic = "Flarlic"
            if color.startswith("ST "):
                flarlic = "ST Flarlic"
            flarlic_count = max(item_count - 2, 0)
            return And(Has(f"{color} Pikmins", item_count),
                       Has(flarlic, flarlic_count),
                       Or(
                           Has(f"{color} Onion"),
                           Has(f"{color} Pikmin Source")
                        )
                       ).resolve(world)


    @dataclasses.dataclass()
    class CanLiftOverWaterRule(Rule["ManualWorld"], game=game_name):
        FreezeCount: int
        Weight: int
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            item_freeze_count = ceil(self.FreezeCount/10)
            item_weight_count = ceil(self.Weight/10)
            return Or(
                Has("Ice Real", item_freeze_count + item_weight_count),
                And(
                    Has("Ice Real", item_freeze_count),
                    CanLiftRule(self.Weight, "Ice"),
                    Has("Flarlic", item_freeze_count + item_weight_count)
                ),
                HasAnyCount({"Blue Real": item_weight_count, "Pink Real": item_weight_count})
            ).resolve(world)

    @dataclasses.dataclass()
    class CanLiftSTRule(Rule["ManualWorld"], game=game_name):
        count: int
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            Real_pikmins = world.event_name_groups["ST Pikmins Carry"]
            max_pikmin_count = ceil(self.count/10)
            return HasFromList(*Real_pikmins, count=max_pikmin_count).resolve(world)

    @dataclasses.dataclass()
    class CanLiftRule(Rule["ManualWorld"], game=game_name):
        count: int
        excluded_colors: str = ""
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            Real_pikmins = world.event_name_groups["Pikmins Carry"]
            excluded = self.excluded_colors.split(";")
            for color in excluded:
                Real_pikmins.remove(f"{color} Real")

            max_pikmin_count = ceil(self.count/10)
            rule: Rule[World]
            if self.count <= 100:
                rule = HasFromList(*Real_pikmins, count=max_pikmin_count) | Has("Purple Real", max_pikmin_count)
                for i in range(max_pikmin_count-1):
                    right = Has("Purple Real", i) & HasFromList(*Real_pikmins, count=max_pikmin_count-i)
                    rule |= right
                return rule.resolve(world)
            else:
                extra = self.count - 100 # to find minimum count of purple 230-100 = 30
                min_purple_count = ceil(extra/100) + 1 # +1 since we can only have 10(100) Real Pikmins Ceil(130/100) = 2
                max_purple_count = ceil(self.count/100)
                rule = Has("Purple Real", max_purple_count) # | (Has("Purple Real", min_purple_count) & HasFromList(*Real_pikmins, count=new_max_pikmin_count))
                for i in range(min_purple_count, max_purple_count):
                    new_max_pikmin_count = min(ceil((self.count - i * 100) / 10), 0) # 230 - 2*100 = 3
                    right = Has("Purple Real", i) & HasFromList(*Real_pikmins, count=new_max_pikmin_count)
                    rule |= right
                return rule.resolve(world)
        # class Resolved(Rule.Resolved):
        #     @override
        #     def explain_str(self, state: CollectionState | None = None) -> str:
        #         return super().explain_str(state)
        #     pass

    @dataclasses.dataclass()
    class HasFromCategoryUniqueRule(Rule["ManualWorld"], game=game_name):
        category: str
        count: str
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            requested_count = int(self.count.strip())
            requested_list = world.item_and_event_name_groups[self.category.strip()]
            return HasFromListUnique(*requested_list, count=requested_count).resolve(world)

    @dataclasses.dataclass()
    class TODORule(Rule["ManualWorld"], game=game_name):
        todo: str
        collect: bool = True
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            TODO(self.todo, self.collect)
            if self.collect:
                return True_().resolve(world)
            else:
                return False_().resolve(world)

    @dataclasses.dataclass()
    class EventValueRule(Rule["ManualWorld"], game=game_name):
        valueCount: str
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            args: list[str] = self.valueCount.split(":")
            if not len(args) == 2 or not args[1].isnumeric():
                raise Exception(f"EventValue needs a number after : so it looks something like 'EventValue({args[0]}:12)'")
            value_name = format_state_prog_items_key("EVENT_VALUE", args[0])
            requested_count = int(args[1].strip())
            return Has(value_name, requested_count).resolve(world)
