from typing import Optional, TYPE_CHECKING, cast, Any
from typing_extensions import override
from NetUtils import JSONMessagePart
from rule_builder.rules import Rule
from worlds.AutoWorld import World
from ..Helpers import clamp, get_items_with_value, is_item_name_enabled, format_state_prog_items_key
from ..Game import game_name
from BaseClasses import MultiWorld, CollectionState
from collections.abc import Mapping
from math import ceil

import dataclasses
import logging
from Utils import version_tuple
# use_rulebuilder = version_tuple >= (0, 6, 7)
from rule_builder.rules import HasFromListUnique, Rule, True_, False_, Has, HasAllCounts, HasAnyCount, \
HasFromList, Or, And, AtLeast, HasAny, OptionFilter
from .Options import GlowPikminUsable, CanRequireMelee
use_full_rules = True

if TYPE_CHECKING:
    from .. import ManualWorld

def Build() -> str:
    return "|Russ|"

def Night(level:int = 1) -> str:
    # TODO adjust depending on level
    pikmin = min(level * 2, 10)
    return f"|Yonny| and |Glow Pikmins:{pikmin}|"

# region ProgBlockers
@dataclasses.dataclass()
class ElectricalGate(Rule["ManualWorld"], game=game_name):
    st: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        if self.st:
            return (Pikmin("ST Yellow") | Bombs("ST")).resolve(world)

        rule: Rule["ManualWorld"] = Or(
            Pikmin("Yellow"), Has("Pup Anti-Electrifier"),
            Has("Anti-Electrifier", options=[OptionFilter(CanRequireMelee, 1)]),
            AnyBomb("WALL")
        )
        return rule.resolve(world)

@dataclasses.dataclass()
class IceGate(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(Pikmin("Red"), Has("Pup Thermal Defense"),
                  Has("Thermal Defense", options=[OptionFilter(CanRequireMelee, 1)]),
                  AnyBomb("WALL"))
        return rule.resolve(world)

def CrystalWall() -> str:
    return "{Pikmin(Rock)} or {AnyBomb(WALL)}"

def ConcreteWall() -> str:
    return '{Bombs()} or {Bombs(track)}'

def BreakPot() -> str:
    return "1"
def BreakPotRule() -> str:
    return "{True_()}"

def DigHole() -> str:
    return "1"
def DigHoleRule() -> str:
    return "{True_()}"

def PushBag() -> str:
    return "1"
def PushBagRule() -> str:
    return "{True_()}"

def LowerBridge() -> str:
    return "1"
def LowerBridgeRule() -> str:
    return "{True_()}"

def DirtWall() -> str:
    return "1"
def DirtWallRule() -> str:
    return "{True_()}"

def PottedPlant() -> str:
    return "1"
def PottedPlantRule() -> str:
    return "{True_()}"

@dataclasses.dataclass()
class FreezeBlob(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        return Or(Pikmin("Ice"), Bombs("Ice")).resolve(world)

@dataclasses.dataclass()
class FreezeWater(Rule["ManualWorld"], game=game_name):
    count: int
    short_duration: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Pikmin("Ice", self.count)
        if self.short_duration:
            rule |= Bombs("Ice")
        return rule.resolve(world)

@dataclasses.dataclass()
class FireFloor(Rule["ManualWorld"], game=game_name):
    from_enemy: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(Pikmin("Red"), Has("Pup Scorch Guard"),
                  Has("Scorch Guard", options=[OptionFilter(CanRequireMelee, 1)]))
        if self.from_enemy:
            rule |= AnyBomb("DMG")
        else:
            rule |= AnyBomb("WALL")
        return rule.resolve(world)

@dataclasses.dataclass()
class PoisonFloorRule(Rule["ManualWorld"], game=game_name):
    can_melee: bool = True
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(Pikmin("White"), Has("Pup Sniff Saver"))
        if self.can_melee:
            rule |= True_(options=[OptionFilter(CanRequireMelee, 1)])
        return rule.resolve(world)
# endregion
# region Items Rules

def CanBoost(st: bool= False) -> str:
    if st:
        return "|ST Boost Potion|"
    return "|Boost Potion|" # TODO check where you can farm for

@dataclasses.dataclass()
class HeadLamp(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(
                                        And(Has("Russ"), EventValueRule("Sparklium:2000")),
                                        Has("NGP")
                                    )
        return And(Has("Headlamp"), rule).resolve(world)

@dataclasses.dataclass()
class Bombs(Rule["ManualWorld"], game=game_name):
    bomb_type: str = "Normal"
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        bomb_type = self.bomb_type.lower()
        rule: Rule["ManualWorld"] = True_()
        if bomb_type == "normal": # TODO check for Source
            rule = And(Or(EventValueRule("Sparklium:3000"), Has("NGP")),
                        Has("Bomb Rocks"))
        elif bomb_type == "st": # TODO check for Source
            rule = Has("ST Bomb Rocks")
        elif bomb_type == "ice":
            rule = And(Or(EventValueRule("Sparklium:1500"), Has("NGP")),
                        Has("Ice Blasts"))
        elif bomb_type == "mine":
            rule = And(Or(EventValueRule("Sparklium:4000"), Has("NGP")),
                                        Has("Mines"))
        elif bomb_type == "track":
            rule = And(Or(EventValueRule("Sparklium:7500"), Has("NGP")),
                                        Has("Trackonators"))
        return And(Has("Russ"), rule).resolve(world)

@dataclasses.dataclass()
class AnyBomb(Rule["ManualWorld"], game=game_name):
    Type: str = ""
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        requested_type = self.Type.upper()
        if requested_type == "ST":
            return Has("ST Bomb Rocks").resolve(world)
        elif requested_type == "DMG":
            return Or(Bombs(), Bombs("Mine"), Bombs("Track")).resolve(world)
        elif requested_type == "WALL":
            return Or(Bombs(), Bombs("Track")).resolve(world)
        return Or(Bombs(),Bombs("Ice"), Bombs("Mine"), Bombs("Track")).resolve(world)


@dataclasses.dataclass()
class Pikmin(Rule["ManualWorld"], game=game_name):
    color: str
    count: int = 1
    quick: bool = False
    convert_to_item: bool = True
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        color = self.color
        count = self.count

        if color.lower() == "purple":
            if self.convert_to_item:
                item_count = ceil(count/100)
            else:
                item_count = count
                count = count * 100
        else:
            if count > 100:
                return False_().resolve(world)
            if self.convert_to_item:
                item_count = ceil(count/10)
            else:
                item_count = count
                count = count * 10
        if self.quick:
            return Has(f"{color} Real", item_count).resolve(world)

        flarlic = "Flarlic"
        flarlic_count = max(item_count - 2, 0)
        if color.startswith("ST "):
            flarlic = "ST Flarlic"
        elif color.lower() == "pup":
            return Has("Buff Learned", _RequiredPup(count)).resolve(world)
        elif color.lower() == "glow":
            return And(Has("Yonny"),Has(f"{color} Pikmins", item_count), options=[OptionFilter(GlowPikminUsable, 1)]).resolve(world)

        return And(HasAllCounts({f"{color} Pikmins": item_count, flarlic: flarlic_count}),
                    HasAny(*[f"{color} Onion",f"{color} Pikmin Source"])).resolve(world)
    # class Resolved(Rule.Resolved):
    #     @override
    #     def  item_dependencies(self) -> dict[str, set[int]]:
    #         return super().item_dependencies()
    #     @override # ? Maybe override the explanation if its too much/weird
    #     def explain_str(self, state: CollectionState | None = None) -> str:
    #         return super().explain_str(state)
    #     @override
    #     def explain_json(self, state: CollectionState | None = None) -> list[JSONMessagePart]:
    #         return super().explain_json(state)

def _RequiredPup(weight: int) -> int:
    import bisect
    # code inspired from https://www.geeksforgeeks.org/python/python-find-closest-number-to-k-in-given-list/
    buff_strenghts = [3, 5, 10, 20, 30, 100]
    # 15
    index = bisect.bisect_right(buff_strenghts, weight)
    # 3
    return index

# endregion
# region CanLift
@dataclasses.dataclass()
class CanLiftST(Rule["ManualWorld"], game=game_name):
    count: int
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        Real_pikmins = set(world.event_name_groups["ST Pikmins Carry"])
        max_pikmin_count = ceil(self.count/10)
        return HasFromList(*Real_pikmins, count=max_pikmin_count).resolve(world)

@dataclasses.dataclass()
class CanLiftOverWater(Rule["ManualWorld"], game=game_name):
    FreezeCount: int
    Weight: int
    PupStatus: int = 2 # 0 NO pup, 1 Pup can touch water, 2 underwater pup
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        FreezeCount = self.FreezeCount
        item_freeze_count = ceil(FreezeCount/10) # 3
        Weight = self.Weight
        item_weight_count = ceil(Weight/10) # 3
        rule: Rule["ManualWorld"]

        if item_weight_count > 10:
            raise NotImplementedError("TODO Implement CanLiftOverWater for weight over 100")
        # Deal with Blue || Pink || Purple
        if use_full_rules:
            rule = Or(Pikmin("Blue", Weight), Pikmin("Pink", Weight), Pikmin("Glow", Weight),
                And(Pikmin("Purple", Weight), Pikmin("Ice", FreezeCount), Has("Flarlic", item_freeze_count - 2 + ceil(Weight / 100)))
            )
            if self.PupStatus:
                rule |= Or(
                    And(Pikmin("pup", Weight), Pikmin("Ice", FreezeCount)),
                    And(Pikmin("pup", Weight), Has("Doggy-Paddle Learned", 1 if self.PupStatus == 1 else 3))
                )
        else:
            rule = Or(HasAnyCount({"Blue Real": item_weight_count, "Pink Real": item_weight_count}), Pikmin("Glow", Weight),
                HasAllCounts({"Purple Real": ceil(Weight / 100), "Ice Real":item_freeze_count, "Flarlic": item_freeze_count - 2 + ceil(Weight / 100)})
            )
            if self.PupStatus:
                rule |= Or(
                    And(Has("Pup Real", item_weight_count), Has("Ice Real", item_freeze_count)),
                    And(Has("Pup Real", item_weight_count), Has("Doggy-Paddle Learned", 1 if self.PupStatus == 1 else 3))
                )
        # Then deal with all the other mix
        max_item_count = item_freeze_count + item_weight_count # 6
        # TODO if max_item_count > 10 need to check for oatchi
        for i in range(item_freeze_count, min(max_item_count, 10)):
            # new_max_pikmin_count = min(ceil((count - (i * 100)) / 10), 0) # ceil((101 - 2*100)/ 10) = ceil(-1 / 10) = -1
            new_max_pikmin_count = min((max_item_count - i), 0) * 10
            right: Rule["ManualWorld"]
            if use_full_rules:
                right = And(Pikmin("Ice", i * 10), Has("Flarlic", max(max_item_count - 2, 8)),
                            CanLift(new_max_pikmin_count, "Ice; Purple" if self.PupStatus else "Ice; Purple; Pup"))
            else:
                right = HasAllCounts({"Ice Real": i, "Flarlic": max(max_item_count - 2, 8)}) &\
                    CanLift(new_max_pikmin_count, "Ice; Purple" if self.PupStatus else "Ice; Purple; Pup")
            rule |= right
        return rule.resolve(world)

@dataclasses.dataclass()
class CanLiftInWater(Rule["ManualWorld"], game=game_name):
    Weight: int
    CloseToSurface: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        Weight = self.Weight
        item_weight_count = ceil(Weight/10) # 3
        rule: Rule["ManualWorld"]

        if item_weight_count > 10:
            raise NotImplementedError("TODO Implement CanLiftInWater for weight over 100")
        # Deal with Blue || Pink
        if use_full_rules:
            rule = Or(Pikmin("Blue", Weight), Pikmin("Glow", Weight),
                And(Pikmin("pup", Weight), Has("Doggy-Paddle Learned", 3)))
            if self.CloseToSurface:
                rule |= Pikmin("Pink", Weight)
        else:
            possible_pikmin = ["Blue Real", "Glow Real", "Pup Real"]
            if self.CloseToSurface:
                possible_pikmin += "Pink Real"
            tmp = HasFromList(*possible_pikmin, options=[OptionFilter(GlowPikminUsable, 1)])
            rule = Or(Has("Blue Real", item_weight_count), Pikmin("Glow", Weight),
                And(Pikmin("pup", Weight), Has("Doggy-Paddle Learned", 3)))
            if self.CloseToSurface:
                rule |= Has("Pink Real", item_weight_count)

        return rule.resolve(world)

@dataclasses.dataclass()
class CanLift(Rule["ManualWorld"], game=game_name):
    count: int
    excluded_colors: str = ""
    invert_excluded: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        if self.count == 0:
            return True_().resolve(world)

        purple_excluded = self.invert_excluded
        if self.invert_excluded and not self.excluded_colors:
            raise Exception("You inverted the excluded colors without 'including' any and thus this CanLift always return False")
        elif self.invert_excluded and self.excluded_colors:
            purple_excluded = True
            Real_pikmins: set[str] = set()
            for color in self.excluded_colors.split(";"):
                color = color.strip()
                if color == "Purple":
                    purple_excluded = False
                    continue
                Real_pikmins.add(f"{color} Real")
        else:
            Real_pikmins = set(world.event_name_groups["Pikmins Carry"])

            if self.excluded_colors:
                for color in self.excluded_colors.split(";"):
                    color = color.strip()
                    if not purple_excluded and color == "Purple":
                        purple_excluded = True
                        continue
                    real_name = f"{color.strip()} Real"
                    if real_name in Real_pikmins:
                        Real_pikmins.remove(real_name)

        max_pikmin_count = ceil(self.count/10)
        world.multiworld.state.prog_items
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

# endregion
# region Standard

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


def HasSomeCount(state: CollectionState, item_counts: Mapping[str, int], player: int, needed: int) -> bool:
    """Returns True if at least "needed" amount of counts is in the state"""
    found = 0
    def has(item: str, count: int = 1):
        return state.has(item, player, count)
    for item, count in item_counts.items():
        if has(item, count):
            found += 1
            if found >= needed:
                return True
    return False

# A rule that checks if the player has at least count of the given items, ignoring duplicates of the same item
def HasFromCategoryUnique(category: str, count: str, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    requested_count = int(count.strip())
    return state.has_from_list_unique(world.item_and_event_name_groups[category], player, requested_count)

@dataclasses.dataclass()
class HasFromCategoryUniqueRule(Rule["ManualWorld"], game=game_name):
    category: str
    count: str
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        requested_count = int(self.count.strip())
        requested_list = world.item_and_event_name_groups[self.category.strip()]
        return HasFromListUnique(*requested_list, count=requested_count).resolve(world)

@dataclasses.dataclass()
class HasSomeCountRule(Rule["ManualWorld"], game=game_name):
    item_counts: Mapping[str, int]
    count: int
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        requested_count = int(self.count)
        children = [Has(item, count) for item, count in self.item_counts.items()]
        return AtLeast(requested_count, *children).resolve(world)

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
# endregion