from typing import Optional, TYPE_CHECKING, cast, Any
from typing_extensions import override
from rule_builder.rules import Rule
from worlds.AutoWorld import World
from ..Helpers import clamp, get_items_with_value, is_item_name_enabled, format_state_prog_items_key
from ..Game import game_name
from BaseClasses import MultiWorld, CollectionState
from math import ceil

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

    return "{Pikmin(Yellow)} or (|Pup Anti-Electrifier|)" + \
        " or (|Anti-Electrifier| and {TODO(Melee Setting)})"

def IceGate() -> str:
    return "{Pikmin(Ice)} or (|Pup Thermal Defense|)" + \
        " or (|Thermal Defense| and {TODO(Melee Setting)})"

def FreezeWater(count: int, short_duration: bool = False) -> str:
    if short_duration:
        return f"{{Pikmin(Ice, {count})}} or {{Bombs(Ice)}}"
    else:
        return f"{{Pikmin(Ice, {count})}}"

def FireFloor() -> str:
    return "{Pikmin(Red)} or (|Pup Scorch Guard|)" + \
        " or (|Scorch Guard| and {TODO(Melee Setting)})"

def PoisonFloor() -> str:
    return "{Pikmin(White)} or (|Pup Sniff Saver|)" + \
        " or {TODO(Melee Setting, False)}"

def Bombs(bomb_type: str = "Normal") -> str:
    bomb_type = bomb_type.lower()
    requires = ""
    if bomb_type == "normal": # TODO check for Source
        requires = "({EventValue(Sparklium:3000)} or |NGP|) and |Bomb Rocks|"
    if bomb_type == "ice":
        requires = "({EventValue(Sparklium:1500)} or |NGP|) and |Ice Blasts|"
    elif bomb_type == "mine":
        requires = "({EventValue(Sparklium:1500)} or |NGP|) and |Mines|"
    elif bomb_type == "track":
        requires = "({EventValue(Sparklium:7500)} or |NGP|) and |Trackonators|"
    return "|Russ| and " + requires

def CanLiftST(count: int, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    # TODO deal with moss pulling stuff
    Real_pikmins =set(world.event_name_groups["ST Pikmins Carry"])
    max_pikmin_count = ceil(count/10)
    return state.has_from_list(Real_pikmins, player, max_pikmin_count)

def CanLiftOverWater(FreezeCount: int, Weight: int, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    # TODO deal with Oatchi pulling stuff + buff upgrade
    Real_pikmins = set(world.event_name_groups["Pikmins Carry"])
    without_ice = set(Real_pikmins)
    without_ice.remove("Ice Real")
    item_freeze_count = ceil(FreezeCount/10)
    item_weight_count = ceil(Weight/10)
    if item_weight_count > 10:
        raise NotImplementedError("TODO Implement CanLiftOverWaterRule for weight over 100")

    # deal with Blue || Pink || Purple + ice
    if (state.has_any_count({"Blue Real": item_weight_count, "Pink Real": item_weight_count}, player)
         or (state.has_all_counts({"Purple Real": 1, "Ice Real": item_freeze_count, "Flarlic": item_freeze_count + 1}, player))):
        return True

    # Then deal with mix of others - purple
    max_item_count = item_freeze_count + item_weight_count # 6
    for i in range(item_freeze_count, max_item_count):
        new_max_pikmin_count = min((max_item_count - i), 0) * 10
        if (state.has_all_counts({"Ice Real": i, "Flarlic": max_item_count}, player)
            and CanLift(new_max_pikmin_count, state, world, player, "Ice; Purple")):
            return True
    return False

def CanLift(count: int, state: CollectionState, world: "ManualWorld", player: int, excluded_colors: str = "") -> bool:
    if count == 0:
        return True
    Real_pikmins = set(world.event_name_groups["Pikmins Carry"])

    purple_excluded = False
    if excluded_colors:
        for color in excluded_colors.split(";"):
            if color.strip() == "Purple":
                purple_excluded = True
                continue
            Real_pikmins.remove(f"{color} Real")

    max_pikmin_count = ceil(count/10)
    rule: bool
    if count <= 100:
        rule = state.has_from_list(Real_pikmins, player, count=max_pikmin_count)
        if not purple_excluded:
            rule |= state.has("Purple Real", player, 1)
        return rule

    else:
        if purple_excluded:
            return False
        extra = count - 100 # to find minimum count of purple 101-100 = 1
        min_purple_count = ceil(extra/100) # ceil(101/100) = 1
        max_purple_count = ceil(count/100) # 2
        if state.has("Purple Real", player, max_purple_count):
            return True
        for i in range(min_purple_count, max_purple_count - 1):
            new_max_pikmin_count = min(ceil((count - (i * 100)) / 10), 0) # ceil((101 - 2*100)/ 10) = ceil(-1 / 10) = -1
            if state.has("Purple Real", player, i) and state.has_from_list(Real_pikmins, player, count=new_max_pikmin_count):
                return True
        return False

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
    from rule_builder.rules import HasFromListUnique, Rule, True_, False_, Has, HasAllCounts, HasAnyCount, HasFromList, Or, And

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
            item_freeze_count = ceil(self.FreezeCount/10) # 3
            item_weight_count = ceil(self.Weight/10) # 3
            if item_weight_count > 10:
                raise NotImplementedError("TODO Implement CanLiftOverWaterRule for weight over 100")
            # Deal with Blue || Pink || Purple
            rule: Rule["ManualWorld"] = HasAnyCount({"Blue Real": item_weight_count, "Pink Real": item_weight_count}) |\
                HasAllCounts({"Purple Real": 1, "Ice Real":item_freeze_count, "Flarlic": item_freeze_count + 1})

            # Then deal with all the other mix
            max_item_count = item_freeze_count + item_weight_count # 6
            for i in range(item_freeze_count, max_item_count):
                # new_max_pikmin_count = min(ceil((count - (i * 100)) / 10), 0) # ceil((101 - 2*100)/ 10) = ceil(-1 / 10) = -1
                new_max_pikmin_count = min((max_item_count - i), 0) * 10
                right = HasAllCounts({"Ice Real": i, "Flarlic": max_item_count}) &\
                    CanLiftRule(new_max_pikmin_count, "Ice; Purple")
                rule |= right
            return rule.resolve(world)

    @dataclasses.dataclass()
    class CanLiftSTRule(Rule["ManualWorld"], game=game_name):
        count: int
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            Real_pikmins = set(world.event_name_groups["ST Pikmins Carry"])
            max_pikmin_count = ceil(self.count/10)
            return HasFromList(*Real_pikmins, count=max_pikmin_count).resolve(world)

    @dataclasses.dataclass()
    class CanLiftRule(Rule["ManualWorld"], game=game_name):
        count: int
        excluded_colors: str = ""
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            # TODO Check for Oatchi buff
            if self.count == 0:
                return True_().resolve(world)
            Real_pikmins = set(world.event_name_groups["Pikmins Carry"])
            purple_excluded = False
            if self.excluded_colors:
                for color in self.excluded_colors.split(";"):
                    if not purple_excluded and color.strip() == "Purple":
                        purple_excluded = True
                        continue
                    Real_pikmins.remove(f"{color.strip()} Real")

            max_pikmin_count = ceil(self.count/10)
            rule: Rule[World]
            if self.count <= 100:
                rule = HasFromList(*Real_pikmins, count=max_pikmin_count)
                if not purple_excluded:
                    rule |= Has("Purple Real", 1)
                return rule.resolve(world)
            else:
                if purple_excluded:
                    return False_().resolve(world)
                extra = self.count - 100 # to find minimum count of purple 230-100 = 130
                min_purple_count = ceil(extra/100) # 130/100 = 1.3 -> 2
                max_purple_count = ceil(self.count/100) # 230/100 = 2.3 -> 3
                rule = Has("Purple Real", max_purple_count)
                for i in range(min_purple_count, max_purple_count - 1):
                    new_max_pikmin_count = min(ceil((self.count - (i * 100)) / 10), 0)
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
