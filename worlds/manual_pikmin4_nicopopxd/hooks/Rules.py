from typing import Optional, TYPE_CHECKING, cast, Any, ClassVar, Counter
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
HasFromList, Or, And, AtLeast, HasAny, OptionFilter, resolve_field, FieldResolver
from .Options import GlowPikminUsable, CanRequireMelee, NewGamePlus
# from . import USE_FULL_RULES

if TYPE_CHECKING:
    from .. import ManualWorld

def Build() -> str:
    return "{Castaway(Russ)}"

def Night(level:int = 1) -> str:
    # TODO adjust depending on level
    pikmin = min(level * 2, 10)
    return f"{{Castaway(Yonny)}} and |Glow Pikmins:{pikmin}|"

def _Castaway(name: str) -> tuple[str, int]:
    RESCUED: tuple[str, ...] = (
        "Russ", "Schnauz", "Kingsly", "Dingo", "Dalmo", "François", "Pitunia", "Yonny", "Puddle", "Mika",
        "Sy", "Sheeba", "Muggs", "Keesh", "Osa", "Frisé", "Kaia", "Vonda", "Twyla", "Don Bergman",
        "Bernise", "Yorke", "Horatio", "Nelle", "Sammy", "Wolfgang"
        )
    BATTLE_LEAFLINGS: tuple[str, ...] = "Dash", "Corgwin", "Bernard", "Olimar"
    LEAFLINGS: tuple[str, ...] = (
        "Jin", "Chet", "Patch", "Chewy", "Molly", "Santi", "Kayz", "Kit", "Komo", "Alpin",
        "Chowder", "Lapi", "Ren", "Boris", "Grace", "Fawks", "Beaux"
        )
    EVENTS: tuple[str, ...] = "Louie",
    if name in RESCUED:
        return "Rescue", RESCUED.index(name) + 3
    elif name in BATTLE_LEAFLINGS:
        return "Battle Leafling Cured", BATTLE_LEAFLINGS.index(name) + 1
    elif name in LEAFLINGS:
        return "Leafling Cured", LEAFLINGS.index(name) + 1
    elif name in EVENTS:
        return name, 1
    raise ValueError(f"'{name}' is not a Known Castaway")

@dataclasses.dataclass()
class Castaways(Rule["ManualWorld"], game=game_name):
    names: str|list[str]
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rescue_max: int = 0
        battle_max: int = 0
        leafling_max: int = 0
        names = self.names
        if isinstance(names, str):
            castaways = names.split(";")
        else:
            castaways = names
        for castaway in castaways:
            castaway = castaway.strip().strip("|")
            item, count = _Castaway(castaway)
            if item == "Rescue" and count > rescue_max:
                rescue_max = count
            elif item == "Battle Leafling Cured" and count > battle_max:
                battle_max = count
            elif item == "Leafling Cured" and count > leafling_max:
                leafling_max = count
        needed: list[tuple[str, int]] = []
        if rescue_max:
            needed.append(("Rescue", rescue_max))
        if battle_max:
            needed.append(("Battle Leafling Cured", battle_max))
        if battle_max:
            needed.append(("Leafling Cured", leafling_max))
        return HasAllCounts(dict(needed), options=self.options).resolve(world)

@dataclasses.dataclass()
class Castaway(Rule["ManualWorld"], game=game_name):
    name: str
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        data = _Castaway(self.name)
        return Has(data[0], data[1], options=self.options).resolve(world)

# region ProgBlockers
@dataclasses.dataclass()
class ElectricalGate(Rule["ManualWorld"], game=game_name):
    st: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        if self.st:
            return (Pikmin("ST Yellow") | Bombs("ST")).resolve(world)

        rule: Rule["ManualWorld"] = Or(
            Pikmin("Yellow"),
            Shop("Pup Anti-Electrifier"),
            Shop("Anti-Electrifier") & CanMelee(),
            AnyBomb("WALL")
        )
        return rule.resolve(world)

@dataclasses.dataclass()
class IceGate(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(
            Pikmin("Red"),
            Shop("Pup Thermal Defense"),
            Shop("Thermal Defense") & CanMelee(),
            AnyBomb("WALL")
        )
        return rule.resolve(world)

def CrystalWall() -> str:
    return "{Pikmin(Rock)} or {AnyBomb(WALL)}"

def ConcreteWall() -> str:
    return '{Bombs()} or {Bombs(track)}'

def BreakPot():
    return True
def BreakPotRule() -> str:
    return "{True_()}"

def DigHole():
    return True
def DigHoleRule() -> str:
    return "{True_()}"

def PushBag():
    return True
def PushBagRule() -> str:
    return "{True_()}"

def LowerBridge():
    return True
def LowerBridgeRule() -> str:
    return "{True_()}"

def DirtWall():
    return True
def DirtWallRule() -> str:
    return "{True_()}"

def PottedPlant():
    return True
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
        if not self.count:
            return True_().resolve(world)
        rule: Rule["ManualWorld"] = Pikmin("Ice", self.count)
        if self.short_duration:
            rule |= Bombs("Ice")
        return rule.resolve(world)

@dataclasses.dataclass()
class FireFloor(Rule["ManualWorld"], game=game_name):
    from_enemy: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(
            Pikmin("Red"),
            Shop("Pup Scorch Guard"),
            Shop("Scorch Guard") & CanMelee()
        )
        if self.from_enemy:
            rule |= AnyBomb("DMG")
        else:
            rule |= AnyBomb("WALL")
        return rule.resolve(world)

@dataclasses.dataclass()
class PoisonFloorRule(Rule["ManualWorld"], game=game_name):
    can_melee: bool = True
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(
            Pikmin("White"),
            Shop("Pup Sniff Saver")
        )
        if self.can_melee:
            rule |= CanMelee()
        return rule.resolve(world)
# endregion
# region Items Rules

def CanBoost(st: bool= False) -> str:
    if st:
        return "|ST Boost Potion|"
    return "|Boost Potion|" # TODO check where you can farm for
@dataclasses.dataclass()
class CanMelee(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Or(
            True_(options=[OptionFilter(CanRequireMelee, CanRequireMelee.option_always)]),
            TripleThreat(options=[OptionFilter(CanRequireMelee, CanRequireMelee.option_with_upgrade)])
        )
        return rule.resolve(world)
@dataclasses.dataclass()
class TripleThreat(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        return Shop("Triple Threat", 8500).resolve(world)

@dataclasses.dataclass()
class HeadLamp(Rule["ManualWorld"], game=game_name):
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        return Shop("Headlamp", 2000).resolve(world)

@dataclasses.dataclass()
class Shop(Rule["ManualWorld"], game=game_name):
    item: str
    unlock_cost: int = 0
    require_russ: bool = False
    item_count: int = 1
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Has(self.item, self.item_count)
        if self.require_russ:
            rule = rule & Castaway("Russ")

        if self.unlock_cost:
            rule = rule & And(Castaway("Russ"), EventValueRule(f"Sparklium:{self.unlock_cost}"),
                            options=[OptionFilter(NewGamePlus, 0)], filtered_resolution=True)
        else:
            rule = rule & Castaway("Russ", options=[OptionFilter(NewGamePlus, 0)], filtered_resolution=True)
        return rule.resolve(world)

@dataclasses.dataclass()
class Bombs(Rule["ManualWorld"], game=game_name):
    bomb_type: str = "Normal"
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        bomb_type = self.bomb_type.lower()
        rule: Rule["ManualWorld"] = True_()
        if bomb_type == "normal": # TODO check for Source
            rule = Shop("Bomb Rocks", 3000, require_russ=True)
        elif bomb_type == "st": # TODO check for Source
            rule = Has("ST Bomb Rocks")
        elif bomb_type == "ice":
            rule = Shop("Ice Blasts", 1500, require_russ=True)
        elif bomb_type == "mine":
            rule = Shop("Mines", 4000, require_russ=True)
        elif bomb_type == "track":
            rule = Shop("Trackonators", 7500, require_russ=True)
        return rule.resolve(world)

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
    weight: int = 1
    quick: bool = False
    convert_to_item: bool = True
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        weight: int = self.weight
        if weight == 0:
            return True_().resolve(world)
        item_counts= self._convert_request_to_items()
        return self.Resolved(
            item_counts=tuple(item_counts.items()),
            color=self.color,
            player=world.player,
            caching_enabled=getattr(world, "rule_caching_enabled", False),
        )
    def _convert_request_to_items(self) -> dict[str, int]:
        color: str = self.color
        weight: int = self.weight
        if weight == 0:
            return {}
        items: dict[str, int] = {}
        if color.lower() == "purple":
            if self.convert_to_item:
                item_count = ceil(weight/100)
            else:
                item_count = weight
                weight = weight * 100
        else:
            if self.convert_to_item:
                item_count = ceil(weight/10)
            else:
                item_count = weight
                weight = weight * 10

        flarlic = "Flarlic"
        flarlic_count = max(item_count - 2, 0)
        if color.startswith("ST "):
            flarlic = "ST Flarlic"
        elif color.lower() == "pup":
            items = {"Buff Learned": _RequiredPup(weight)}
        elif color.lower() == "glow":
            options = list(self.options)
            options.append(OptionFilter(GlowPikminUsable, 1))
            self.options = options
            yonny = _Castaway("Yonny")
            items = {f"{color} Pikmins": item_count, yonny[0]: yonny[1]}
        else:
            items = {f"{color} Pikmins": item_count}
            if flarlic_count:
                items[flarlic] = flarlic_count
            items[f"Source"] = 1
        return items

    @override
    def __str__(self) -> str:
        def _count(count:int) -> str:
            return f" x{count}" if count > 1 else ""
        items = ", ".join([f"{item}{_count(count)}" for item, count in self._convert_request_to_items().items()])
        options = f", options={self.options}" if self.options else ""
        return f"{self.__class__.__name__}({items}{options})"
    class Resolved(Rule.Resolved):
        item_counts: tuple[tuple[str, int], ...]
        color: str
        @override
        def _evaluate(self, state: CollectionState) -> bool:
            def _has(item:str, count: int = 1) -> bool:
                return state.has(item, player, count)
            player = self.player
            item_counts = dict(self.item_counts)
            color = self.color
            Source = item_counts.pop("Source", None)
            for item, count in item_counts.items():
                if not _has(item, count):
                    return False
            if Source is not None:
                if not (_has(f"{color} Onion") or _has(f"{color} Pikmin Source")):
                    return False
            return True
        @override
        def item_dependencies(self) -> dict[str, set[int]]:
            items: dict[str, set[int]] = {}
            item_counts = dict(self.item_counts)
            color = self.color
            Source = item_counts.pop("Source", None)
            if Source is not None:
                item_counts[f"{color} Onion"] = 42
                item_counts[f"{color} Pikmin Source"] = 42

            for item in item_counts:
                items[item] = {id(self)}
            return items
        @override
        def explain_str(self, state: CollectionState | None = None) -> str:
            if state is None:
                return self.__str__()
            player = self.player
            item_counts = dict(self.item_counts)
            pikmin_color = self.color
            main_count = self.item_counts[0][1]
            if pikmin_color.lower() == "pup":
                prefix = "Has" if self(state) else "Missing"
                count_str = f"{main_count}x " if main_count > 1 else ""
                return f"{prefix} {count_str}Buff Learned"
            Source = item_counts.pop("Source", None)
            final_str = ""
            def _count(item:str) -> int:
                return state.count(item, player)
            def _has(item: str) -> bool:
                return _count(item) >= item_counts[item]
            for i, (item, count) in enumerate(item_counts.items()):
                if i > 0:
                    final_str += ", "
                if _has(item):
                    final_str += "[x] "
                    if count > 1:
                        final_str += f"{count} "
                else:
                    final_str += "[ ] "
                    if count > 1:
                        final_str += f"{_count(item)}/{count} "
                final_str += item
            if Source:
                onion = f"{pikmin_color} Onion"
                has_onion = _has(onion)
                source = f"{pikmin_color} Pikmin Source"
                has_source = _has(source)
                final_str += f", [{'X' if has_onion or has_source else ' '}] Source"
                if not (has_onion or has_source):
                    final_str += f"({onion} OR {source})"
            return final_str
        @override
        def explain_json(self, state: CollectionState | None = None) -> list[JSONMessagePart]:
            player = self.player
            messages: list[JSONMessagePart] = []
            item_counts = dict(self.item_counts)
            Source = item_counts.pop("Source", None)
            pikmin_color = self.color
            main_count = self.item_counts[0][1]
            def str_count(count:int) -> str:
                return f"{count}x " if count > 1 else ""
            if state is None:
                count_str = str_count(main_count)
                if pikmin_color.lower() == "pup":
                    messages = [{"type": "text", "text": "Has "}]
                    if count_str:
                        messages.extend([
                        {"type": "color", "color": "cyan", "text": str(main_count)},
                        {"type": "text", "text": "x "},
                    ])
                    messages.append({"type": "item_name", "flags": 0b001, "text": "Buff Learned", "player": self.player})
                else:
                    messages = [{"type": "text", "text": "Has "}]
                    for i, (item, count) in enumerate(item_counts.items()):
                        if i > 0:
                            messages.append({"type": "text", "text": ", "})
                        count_str = str_count(count)
                        if count_str:
                            messages.extend([
                                {"type": "color", "color": "cyan", "text": str(count)},
                                {"type": "text", "text": "x "},
                            ])
                        messages.append({"type": "item_name", "flags": 0b001, "text": item, "player": self.player})
                    if Source is not None:
                        messages.extend([
                            {"type": "text", "text": "and any of ("},
                            {"type": "item_name", "flags": 0b001, "text": f"{pikmin_color} Onion", "player": self.player},
                            {"type": "text", "text": ","},
                            {"type": "item_name", "flags": 0b001, "text": f"{pikmin_color} Pikmin Source", "player": self.player},
                        ])
                        messages.append({"type": "text", "text": ")"})
                return messages

            def _has(item:str, count: int = 1) -> bool:
                return state.has(item, player, count)
            def _count(item:str) -> int:
                return state.count(item, player)

            def _color(have:int, want: int) -> str:
                return "green" if have >= want else "salmon"

            if pikmin_color.lower() == "pup":
                verb = "Missing " if state and not self(state) else "Has "
                messages.append({"type": "text", "text": verb})
                if main_count > 1:
                    messages.append({"type": "color", "color": "cyan", "text": str(main_count)})
                    messages.append({"type": "text", "text": "x "})

                color = "green" if self(state) else "salmon"
                messages.append({"type": "color", "color": color, "text": "Buff Learned"})
                return messages
            main_actual_count = _count(self.item_counts[0][0])
            item_counts.pop(f"{pikmin_color} Pikmins", None)
            messages = [
                {"type": "text", "text": "Has "},
                {
                    "type": "color",
                    "color": _color(main_actual_count, main_count),
                    "text": f"{main_actual_count}/{main_count}" if main_actual_count < main_count else str(main_count),
                },
                {"type": "text", "text": f" {pikmin_color} Pikmins"},
            ]
            if item_counts:
                for item, count in item_counts.items():
                    actual_count = _count(item)
                    count_str = f"{actual_count}/{count} " if actual_count < count else f"{count} "
                    item_str = f"{count_str if str_count(count) else ''}{item}"
                    messages.extend([
                        {"type": "text", "text": ", "},
                        {
                            "type": "color",
                            "color": _color(actual_count, count),
                            "text": item_str,
                        }])
            if Source:
                onion = f"{pikmin_color} Onion"
                has_onion = _has(onion)
                source = f"{pikmin_color} Pikmin Source"
                has_source = _has(source)
                messages.extend([
                    {"type": "text", "text": " and "},
                    {
                        "type": "color",
                        "color": _color(int(has_onion) + int(has_source) , 1),
                        "text": "Source",
                    }])
                if not (has_onion or has_source):
                    messages.extend([
                    {"type": "text", "text": " ("},
                    {
                        "type": "color",
                        "color": _color(int(has_onion), 1),
                        "text": onion,
                    },
                    {"type": "text", "text": " or "},
                    {
                        "type": "color",
                        "color": _color(int(has_source), 1),
                        "text": source,
                    },
                    ])
            return messages
        @override
        def __str__(self) -> str:
            item_counts = dict(self.item_counts)
            def _count(count:int) -> str:
                return f"{count}x " if count > 1 else ""
            color = self.color
            main_count = self.item_counts[0][1]
            if color.lower() == "pup":
                return f"Has {_count(main_count)}Buff Learned"
            flarlic_type: str = 'Flarlic' if 'Flarlic' in item_counts else 'ST Flarlic' if 'ST Flarlic' in item_counts else ""
            flarlic_str = f" & {_count(item_counts[flarlic_type])} {flarlic_type}" if flarlic_type else ""
            return f"Has {_count(main_count)}{self.color} Pikmins & Source{flarlic_str}"

def _RequiredPup(weight: int) -> int:
    import bisect
    # code inspired from https://www.geeksforgeeks.org/python/python-find-closest-number-to-k-in-given-list/
    buff_strenghts = [3, 5, 10, 20, 30, 100]
    # 15
    index = bisect.bisect_right(buff_strenghts, weight)
    # 3
    return index
def _PupToWeight(item:int) -> int:
    buff_strenghts = [3, 5, 10, 20, 30, 100]
    if item <= len(buff_strenghts):
        return buff_strenghts[item-1]
    return buff_strenghts[-1]
# endregion
# region CanLift
@dataclasses.dataclass()
class CanLiftST(Rule["ManualWorld"], game=game_name):
    weight: int
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        colors = [c.removesuffix(" Pikmins") for c in sorted(world.item_name_groups["ST Pikmins"]) if c.endswith(" Pikmins")]
        # TODO Handle Moss somehow (probably in PupStatus > 3)
        # Real_pikmins = [i for i in sorted(world.event_name_groups["ST Pikmins Carry"])]
        # max_pikmin_count = ceil(self.weight/10)
        # return HasFromList(*Real_pikmins, count=max_pikmin_count).resolve(world)
        return CanLift(self.weight, colors, True, 0).resolve(world)

@dataclasses.dataclass()
class CanLiftOverWater(Rule["ManualWorld"], game=game_name):
    """A rule that checks if the player has enough pikmin + pup to lift an item over the water"""
    FreezeCount: int
    Weight: int
    PupStatus: int = 2 # 0 NO pup, 1 Pup can touch water, 2 underwater pup
    InACave: bool = False # For Glow Pikmins
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        FreezeCount = self.FreezeCount
        Weight = self.Weight
        rule: Rule["ManualWorld"]

        # Deal with Blue or Pink or Glow || Purple
        rule = Or(
            CanLiftInWater(Weight, True, self.PupStatus, self.InACave),
            FreezeWater(FreezeCount) & CanLift(Weight, InACave=self.InACave, previous_pikmin={"Ice":FreezeCount})
        )

        return rule.resolve(world)

@dataclasses.dataclass()
class CanLiftInWater(Rule["ManualWorld"], game=game_name):
    """A rule that checks if the player has enough pikmin + pup to lift an item in water"""
    Weight: int
    CloseToSurface: bool = False
    PupStatus: int = 2 if CloseToSurface else 1
    InACave: bool = False # For Glow Pikmins
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        Weight = self.Weight
        rule: Rule["ManualWorld"]
        colors = ["Blue", "Glow"]
        if self.CloseToSurface:
            colors.append("Pink")

        rule = CanLift(Weight, colors, True, self.PupStatus + 1 if self.PupStatus else 0, self.InACave)
        return rule.resolve(world)

@dataclasses.dataclass()
class CanLift(Rule["ManualWorld"], game=game_name):
    """A rule that checks if the player has enough pikmin + pup to lift an item"""
    weight: int | FieldResolver
    """How much does the item weight"""
    excluded_colors: str | list[str] = dataclasses.field(default_factory=list)
    """`;` separated list of pikmin color to include /exclude if `invert_excluded`"""
    invert_excluded: bool | FieldResolver = False
    """Should `excluded_color` be used as included instead"""
    pup_status: int | FieldResolver = 1
    """
    0. No Oatchi
    1. Yes Oatchi # default
    2. Oatchi might need to touch water aka |Doggy-Paddle Learned:1|
    3. Oatchi might swim aka |Doggy-Paddle Learned:3|
    """
    InACave: bool = False # For Glow Pikmins
    previous_pikmin: str | dict[str, int] = dataclasses.field(default_factory=dict)
    """For things like freezing the water"""
    @override
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        weight = resolve_field(self.weight, world, int)
        previous_pikmin = self.previous_pikmin
        if isinstance(previous_pikmin, str):
            def _build_dict(data:str) -> tuple[str, int]:
                data_list = data.split(":")
                count = 0
                if len(data_list) > 1:
                    count = int(data_list[-1])
                return data_list[0], count
            previous_pikmin = {_build_dict(i)[0]: _build_dict(i)[1] for i in previous_pikmin.strip().split(";")}
        if weight <= 0:
            return True_().resolve(world)
        excluded_colors = self.excluded_colors
        if isinstance(excluded_colors, str):
            excluded_colors = excluded_colors.strip().split(";")
        invert_excluded = resolve_field(self.invert_excluded, world, bool)
        pup_status = resolve_field(self.pup_status, world, int)
        colors = {c.removesuffix(" Pikmins") for c in sorted(world.item_name_groups["Pikmins"]) if c.endswith(" Pikmins")}
        if invert_excluded and not excluded_colors:
            raise Exception("You inverted the excluded colors without 'including' any and thus this CanLift always return False")

        elif invert_excluded and excluded_colors:
            pikmins: set[str] = set()
            for color in excluded_colors:
                color = color.strip()
                if color == "Pup":
                    continue
                pikmins.add(color)

        else:
            pikmins = set(colors)
            if excluded_colors:
                for color in excluded_colors:
                    color = color.strip()
                    if color == "Pup":
                        continue
                    if color in pikmins:
                        pikmins.remove(color)

        Glow_Pikmin_In_Caves = getattr(world.options, "Glow_Pikmin_In_Caves", GlowPikminUsable(GlowPikminUsable.default)).value
        if not (Glow_Pikmin_In_Caves and self.InACave) and "Glow" in pikmins:
            pikmins.remove("Glow")

        for pikmin in tuple(pikmins):
            if previous_pikmin.get(pikmin, 0) == 100:
                pikmins.remove(pikmin)

        return self.Resolved(
            weight=weight,
            previous_pikmin=tuple(previous_pikmin.items()),
            pup_status=pup_status,
            valid_pikmins=tuple(sorted(pikmins)),
            player=world.player,
            caching_enabled=getattr(world, "rule_caching_enabled", False),
        )

    @override
    def __str__(self) -> str:
        count = f"weight={self.weight}" if isinstance(self.weight, FieldResolver) or self.weight > 1 else ""
        options = f", options={self.options}" if self.options else ""
        return f"{self.__class__.__name__}({count}{options})"

    class Resolved(Rule.Resolved):
        weight: int
        previous_pikmin: tuple[tuple[str, int], ...]
        pup_status: int
        valid_pikmins: tuple[str, ...]
        skip_cache: ClassVar[bool] = True

        @override
        def _evaluate(self, state: CollectionState) -> bool:
            player = self.player
            def _has(item:str, count: int = 1) -> bool:
                return state.has(item, player, count)
            def _count(item:str) -> int:
                return state.count(item, player)
            extra_count = 0
            max_pikmin = 100
            previous_pikmin = Counter(dict(self.previous_pikmin))
            for count in previous_pikmin.values():
                max_pikmin -= count
                extra_count += count

            def _clamp(pikmin_count:int) -> int:
                return min(pikmin_count, max_pikmin)
            to_lift = self.weight
            if self.pup_status:
                pup_count = _count("Buff Learned")
                if self.pup_status in [2,3]:
                    if _has("Doggy-Paddle Learned", 1 if self.pup_status == 2 else 3):
                        to_lift -= _PupToWeight(pup_count)
                else:
                    to_lift -= _PupToWeight(pup_count)
                if to_lift <= 0: return True
            purple_count = 0
            valid_pikmins = list(self.valid_pikmins)
            if "Purple" in valid_pikmins:
                valid_pikmins.pop(valid_pikmins.index("Purple"))
                count = 0
                if _has("Purple Onion") or _has("Purple Pikmin Source"):
                    count = _count("Purple Pikmins") * 10

                if "Purple" in previous_pikmin:
                    count -= previous_pikmin["Purple"]
                count = _clamp(count)
                if count > 0:
                    purple_count = count
                    to_lift -= count*10
                    if to_lift <= 0: return True
                    max_pikmin -= count
                    extra_count += count
            if to_lift > 100 or not valid_pikmins or max_pikmin <= 0: return False # if we get here then pup + purple failed

            pool: Counter[str] = Counter()
            if "Glow" in valid_pikmins: # Glow do not need Flarlics so don't check for those here
                count = 0
                if _has(*_Castaway("Yonny")):
                    count = _count("Glow Pikmins")

                if "Glow" in previous_pikmin:
                    count -= previous_pikmin["Glow"]
                count = _clamp(count)
                if count > 0:
                    to_lift -= count
                    if to_lift <= 0: return True
                    max_pikmin -= count
                    extra_count += count

            if to_lift > max_pikmin: return False # even if we could have pikmin we couldn't have enough

            flarlic_count = max(ceil((previous_pikmin.total() + purple_count + to_lift)/10) - 2, 0)
            if not _has("Flarlic", flarlic_count): return False

            for color in valid_pikmins:
                if color in ["Glow", "Purple"]: continue
                count = 0
                if _has(f"{color} Onion") or _has(f"{color} Pikmin Source"):
                    count = _count(f"{color} Pikmins")
                if color in previous_pikmin:
                    count -= previous_pikmin[color]
                if count > 0:
                    pool[color] = count
                if pool.total() >= to_lift: return True

            return False

        @override
        def item_dependencies(self) -> dict[str, set[int]]:
            items: dict[str, set[int]] = {}
            if self.pup_status:
                items["Buff Learned"] = {id(self)}
                if self.pup_status > 1:
                    items["Doggy-Paddle Learned"] = {id(self)}
            if self.valid_pikmins:
                items["Flarlic"] = {id(self)}
            for color in self.valid_pikmins:
                items[f"{color} Pikmins"] = {id(self)}
                if color == "Glow":
                    items[_Castaway("Yonny")[0]] = {id(self)}
                    continue
                items[f"{color} Onion"] = {id(self)}
                items[f"{color} Pikmin Source"] = {id(self)}
            return items

        @override
        def explain_json(self, state: CollectionState | None = None) -> list[JSONMessagePart]:
            messages: list[JSONMessagePart] = []
            if state is None:
                messages = [
                    {"type": "text", "text": "Has Enough "},
                    {"type": "color", "color": "cyan", "text": "Lift Power"},
                    {"type": "text", "text": " To lift "},
                    {"type": "color", "color": "cyan", "text": f"{self.weight}"},
                    {"type": "text", "text": "x out of ("},
                ]
                items: list[str] = []
                if self.pup_status:
                    items.append("Buff Learned")
                    if self.pup_status in [2,3]:
                        items.append("Doggy-Paddle Learned")

                for color in self.valid_pikmins:
                    items.append(f"{color} Pikmins")
                    if color == "Glow":
                        items.append(_Castaway("Yonny")[0])
                        continue
                    items.append(f"{color} Onion")
                    items.append(f"{color} Pikmin Source")

                for i, item in enumerate(items):
                    if i > 0:
                        messages.append({"type": "text", "text": ", "})
                    messages.append({"type": "item_name", "flags": 0b001, "text": item, "player": self.player})
                messages.append({"type": "text", "text": ")"})
                return messages
            pool, pup_lift, purple_lift, found, missing = self._fill_found_missing_lists(state)
            messages = [
                {"type": "text", "text": "Has Enough" if found else "Not Enough"},
                {"type": "text", "text": " for "},
                {"type": "color", "color": "cyan", "text": f"{self.weight}x Lift Power"},
                {"type": "text", "text": " ("},
            ]
            total_str = f"{pup_lift + purple_lift + min(pool.total(), 100)}"
            if self(state):
                messages.append({"type": "color", "color": "green", "text": f"{total_str}"})
                messages.append({"type": "text", "text": "/"})
                messages.append({"type": "color", "color": "cyan", "text": f"{self.weight}"})
                messages.append({"type": "text", "text": ")"})
                return messages
            else:
                messages.append({"type": "color", "color": "salmon", "text": f"{total_str}"})
                messages.append({"type": "text", "text": "/"})
                messages.append({"type": "color", "color": "cyan", "text": f"{self.weight}"})
                messages.append({"type": "text", "text": " "})

            if found:
                messages.append({"type": "text", "text": "Found: "})
                for i, item in enumerate(found):
                    if i > 0:
                        messages.append({"type": "text", "text": ", "})
                    messages.append({"type": "color", "color": "green", "text": item})
                if missing:
                    messages.append({"type": "text", "text": "; "})
            if missing:
                messages.append({"type": "text", "text": "Missing (Pikmins and/or a Source): "})
                for i, item in enumerate(missing):
                    if i > 0:
                        messages.append({"type": "text", "text": ", "})
                    messages.append({"type": "color", "color": "salmon", "text": item})
            messages.append({"type": "text", "text": ")"})
            return messages

        def _fill_found_missing_lists(self, state: CollectionState) -> tuple[Counter[str], int, int, list[str], list[str]]:
            player = self.player
            def _has(item:str, count: int = 1) -> bool:
                return state.has(item, player, count)
            def _count(item:str) -> int:
                return state.count(item, player)

            pool: Counter[str] = Counter()
            previous_pikmin = Counter(dict(self.previous_pikmin))
            pup_lift = 0
            purple_count = 0
            valid_pikmins = self.valid_pikmins
            if self.pup_status:
                pup_lift = _PupToWeight(_count("Buff Learned"))

            for color in valid_pikmins:
                count = 0
                if color == "Glow" and _has(*_Castaway("Yonny")): # Glow do not need Flarlics so don't check for those
                    count = _count("Glow Pikmins") * 10
                    continue
                if _has(f"{color} Onion") or _has(f"{color} Pikmin Source"):
                    count = _count(f"{color} Pikmins") * 10

                count -= previous_pikmin.get(color, 0)
                if count > 0:
                    if color == "Purple":
                        purple_count = count
                        count *= 10
                    pool[color] = count
            missing: list[str] = []

            found = []
            if self.pup_status:
                buff_count = _count("Buff Learned")
                if buff_count < 6:
                    missing.append(f"Oatchi: {6 - buff_count}")
                found.append(f"Oatchi: {pup_lift} ({buff_count}/6)")
                paddle_needed: int = 0 if self.pup_status < 2 else  1 if self.pup_status == 2 else 3
                paddle_count = _count('Doggy-Paddle Learned')
                if paddle_needed:
                    if not _has("Doggy-Paddle Learned", paddle_needed):
                        missing.append(f"Doggy-Paddle Learned: {paddle_needed - paddle_count}/{paddle_needed}")
                    else:
                        found.append(f"Doggy-Paddle Learned: {paddle_count}/{paddle_needed}")
            purple_lift = pool["Purple"]
            to_lift = self.weight - pup_lift - purple_lift
            rough_flarlic = ceil((to_lift + purple_count + previous_pikmin.total())/10)
            flarlic_count = max(rough_flarlic - 2 - pool["Glow"], 0)
            if not _has("Flarlic", flarlic_count):
                missing.extend(f"Flarlic: {flarlic_count - _count('Flarlic')}")
            missing.extend([color for color in valid_pikmins if color not in pool.keys()
                            or (pool[color] < 100 if color != "Purple" else pool[color] < 1000)])
            found.extend([f"{color}: {count}" for color, count in pool.items()])

            return pool, pup_lift, purple_lift, found, missing

        @override
        def explain_str(self, state: CollectionState | None = None) -> str:
            if state is None:
                return str(self)
            pool, pup_lift, purple_lift, found, missing = self._fill_found_missing_lists(state)
            found_str = f"Found: {', '.join(found)}" if found else ""
            missing_str = f"Missing: {', '.join(missing)}" if missing else ""
            infix = "; " if found_str and missing else ""

            total_str = f"{pup_lift + purple_lift + min(pool.total(), 100)}"
            prefix: str = "Has Enough" if self(state) else "Not Enough"
            suffix: str = "" if self(state) else f" from {found_str}{infix}{missing_str}"
            return f"{prefix} for {self.weight}x Lift Power ({total_str}/{self.weight}{suffix})"

        @override
        def __str__(self) -> str:
            count = f"{self.weight}x " if self.weight > 1 else ""
            Oatchi_str = "Oatchi, " if self.pup_status else ""
            paddle_needed: int = 0 if self.pup_status < 2 else  1 if self.pup_status == 2 else 3
            if paddle_needed:
                Oatchi_str += f"Doggy-Paddle Learned ({paddle_needed}), "
            sources: str = Oatchi_str
            colors_count = len(self.valid_pikmins)# + int(not self.purple_excluded)
            offset = 1 if "Glow" not in self.valid_pikmins else 0
            if colors_count == 9 - offset: # All pikmins
                sources += "Any"
                pass
            elif colors_count > 4: # more than half, invert
                all_colors = {"Red", "Yellow", "Blue", "Pink", "Ice", "Rock", "Purple", "White"}
                compareto = set(self.valid_pikmins)
                reversed_colors = all_colors - compareto
                sources += "Any Pikmins + Source Except; "
                sources += " Pikmins + Source, ".join(sorted(reversed_colors))
            else:
                sources += " Pikmins + Source, ".join(self.valid_pikmins)
            if self.valid_pikmins:
                sources += " Pikmins + Source"
            return f"Has Enough {count}Lift Power from ({sources})"

# endregion

# region laboratory

# @dataclasses.dataclass()
# class _Has(Rule["ManualWorld"], game=game_name):
#     """A rule that checks if the player has at least `count` of a given item"""

#     item_name: str | FieldResolver
#     """The item to check for"""

#     count: int | FieldResolver = 1
#     """The count the player is required to have"""

#     @override
#     def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
#         count = resolve_field(self.count, world, int)
#         if count <= 0:
#             return True_().resolve(world)
#         return self.Resolved(
#             resolve_field(self.item_name, world, str),
#             count=count,
#             player=world.player,
#             caching_enabled=getattr(world, "rule_caching_enabled", False),
#         )

#     @override
#     def __str__(self) -> str:
#         count = f", count={self.count}" if isinstance(self.count, FieldResolver) or self.count > 1 else ""
#         options = f", options={self.options}" if self.options else ""
#         return f"{self.__class__.__name__}({self.item_name}{count}{options})"

#     class Resolved(Rule.Resolved):
#         item_name: str
#         count: int = 1
#         skip_cache: ClassVar[bool] = True

#         @override
#         def _evaluate(self, state: CollectionState) -> bool:
#             # implementation based on state.has
#             return state.prog_items[self.player][self.item_name] >= self.count

#         @override
#         def item_dependencies(self) -> dict[str, set[int]]:
#             return {self.item_name: set()}

#         @override
#         def explain_json(self, state: CollectionState | None = None) -> list[JSONMessagePart]:
#             verb = "Missing " if state and not self(state) else "Has "
#             messages: list[JSONMessagePart] = [{"type": "text", "text": verb}]
#             if self.count > 1:
#                 messages.append({"type": "color", "color": "cyan", "text": str(self.count)})
#                 messages.append({"type": "text", "text": "x "})
#             if state:
#                 color = "green" if self(state) else "salmon"
#                 messages.append({"type": "color", "color": color, "text": self.item_name})
#             else:
#                 messages.append({"type": "item_name", "flags": 0b001, "text": self.item_name, "player": self.player})
#             return messages

#         @override
#         def explain_str(self, state: CollectionState | None = None) -> str:
#             if state is None:
#                 return str(self)
#             prefix = "Has" if self(state) else "Missing"
#             count = f"{self.count}x " if self.count > 1 else ""
#             return f"{prefix} {count}{self.item_name}"

#         @override
#         def __str__(self) -> str:
#             count = f"{self.count}x " if self.count > 1 else ""
#             return f"Has {count}{self.item_name}"


# @dataclasses.dataclass()
# class OldPikmin(Rule["ManualWorld"], game=game_name):
#     color: str
#     count: int = 1
#     quick: bool = False
#     convert_to_item: bool = True
#     def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
#         color = self.color
#         count = self.count
#         if count == 0:
#             return True_().resolve(world)

#         if color.lower() == "purple":
#             if self.convert_to_item:
#                 item_count = ceil(count/100)
#             else:
#                 item_count = count
#                 count = count * 100
#         else:
#             if count > 100:
#                 return False_().resolve(world)
#             if self.convert_to_item:
#                 item_count = ceil(count/10)
#             else:
#                 item_count = count
#                 count = count * 10
#         if self.quick and not USE_FULL_RULES:
#             return Has(f"{color} Real", item_count).resolve(world)

#         flarlic = "Flarlic"
#         flarlic_count = max(item_count - 2, 0)
#         if color.startswith("ST "):
#             flarlic = "ST Flarlic"
#         elif color.lower() == "pup":
#             return Has("Buff Learned", _RequiredPup(count)).resolve(world)
#         elif color.lower() == "glow":
#             return And(Has("Yonny"),Has(f"{color} Pikmins", item_count), options=[OptionFilter(GlowPikminUsable, 1)]).resolve(world)

#         return And(HasAllCounts({f"{color} Pikmins": item_count, flarlic: flarlic_count}),
#                     HasAny(*[f"{color} Onion",f"{color} Pikmin Source"])).resolve(world)
#     # class Resolved(Rule.Resolved):
#     #     @override
#     #     def  item_dependencies(self) -> dict[str, set[int]]:
#     #         return super().item_dependencies()
#     #     @override # ? Maybe override the explanation if its too much/weird
#     #     def explain_str(self, state: CollectionState | None = None) -> str:
#     #         return super().explain_str(state)
#     #     @override
#     #     def explain_json(self, state: CollectionState | None = None) -> list[JSONMessagePart]:
#     #         return super().explain_json(state)
#     #     @override
#     #     def __str__(self) -> str:
#     #         count = f"{self.weight}x " if self.weight > 1 else ""
#     #         Oatchi_str = "Oatchi, " if self.pup_status else ""
#     #         paddle_needed: int = 0 if self.pup_status < 2 else  1 if self.pup_status == 2 else 3
#     #         if paddle_needed:
#     #             Oatchi_str += f"Doggy-Paddle Learned ({paddle_needed}), "
#     #         sources: str = Oatchi_str
#     #         sources += "Purple Pikmins + Source, " if not self.purple_excluded else ""
#     #         sources += " Pikmins + Source, ".join(self.valid_pikmins)
#     #         return f"Have enough {count}Lift Power from ({sources})"

# @dataclasses.dataclass()
# class OldCanLift(Rule["ManualWorld"], game=game_name):
#     # TODO potentially rewrite to count pup first then pikmin
#     count: int
#     excluded_colors: str = ""
#     invert_excluded: bool = False
#     def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
#         if self.count == 0:
#             return True_().resolve(world)

#         purple_excluded = self.invert_excluded
#         if self.invert_excluded and not self.excluded_colors:
#             raise Exception("You inverted the excluded colors without 'including' any and thus this CanLift always return False")
#         elif self.invert_excluded and self.excluded_colors:
#             purple_excluded = True
#             Real_pikmins: set[str] = set()
#             for color in self.excluded_colors.split(";"):
#                 color = color.strip()
#                 if color == "Purple":
#                     purple_excluded = False
#                     continue
#                 Real_pikmins.add(f"{color} Real")
#         else:
#             Real_pikmins = set(world.event_name_groups["Pikmins Carry"])

#             if self.excluded_colors:
#                 for color in self.excluded_colors.split(";"):
#                     color = color.strip()
#                     if not purple_excluded and color == "Purple":
#                         purple_excluded = True
#                         continue
#                     real_name = f"{color.strip()} Real"
#                     if real_name in Real_pikmins:
#                         Real_pikmins.remove(real_name)

#         max_pikmin_count = ceil(self.count/10)
#         rule: Rule[World]
#         if self.count <= 100:
#             rule = HasFromList(*Real_pikmins, count=max_pikmin_count)
#             if not purple_excluded:
#                 rule |= Has("Purple Real", 1)
#             return rule.resolve(world)
#         else:
#             if purple_excluded:
#                 return False_().resolve(world)
#             extra = self.count - 100 # to find minimum count of purple 230-100 = 130
#             min_purple_count = ceil(extra/100) # 130/100 = 1.3 -> 2
#             max_purple_count = ceil(self.count/100) # 230/100 = 2.3 -> 3
#             rule = Has("Purple Real", max_purple_count)
#             for i in range(min_purple_count, max_purple_count - 1):
#                 new_max_pikmin_count = min(ceil((self.count - (i * 100)) / 10), 0)
#                 right = Has("Purple Real", i) & HasFromList(*Real_pikmins, count=new_max_pikmin_count)
#                 rule |= right
#             return rule.resolve(world)

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