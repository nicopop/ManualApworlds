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
from .Options import GlowPikminUsable, CanRequireMelee
from . import USE_FULL_RULES

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
    cost: int = 0
    require_russ: bool = False
    item_count: int = 1
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        rule: Rule["ManualWorld"] = Has("NGP")
        if self.require_russ:
            rule = rule & Has("Russ")
        if self.cost:
            rule |= Has("Russ") & EventValueRule(f"Sparklium:{self.cost}")
        else:
            rule |= Has("Russ")

        if self.item is not None:
            rule = rule & Has(self.item, self.item_count)
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
    count: int = 1
    quick: bool = False
    convert_to_item: bool = True
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        color = self.color
        count = self.count
        if count == 0:
            return True_().resolve(world)

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
        if self.quick and not USE_FULL_RULES:
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
def _PupToWeight(item:int) -> int:
    buff_strenghts = [3, 5, 10, 20, 30, 100]
    if item <= len(buff_strenghts):
        return buff_strenghts[item-1]
    return buff_strenghts[-1]
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
    """A rule that checks if the player has enough pikmin + pup to lift an item over the water"""
    FreezeCount: int
    Weight: int
    PupStatus: int = 2 # 0 NO pup, 1 Pup can touch water, 2 underwater pup
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        FreezeCount = self.FreezeCount
        item_freeze_count = ceil(FreezeCount/10) # 3
        Weight = self.Weight
        item_weight_count = ceil(Weight/10) # 3
        rule: Rule["ManualWorld"]

        # Deal with Blue or Pink or Glow || Purple
        rule = Or( # v Blue or Pink or Glow
            CanLiftInWater(Weight, True), # v ice freeze + anything but ice
            FreezeWater(FreezeCount) & CanLift(Weight, ["Ice"], previous_pikmin_count=FreezeCount)
        )

        # Then deal with all the other mix
        max_item_count = item_freeze_count + item_weight_count # 6
        for i in range(item_freeze_count, min(max_item_count, 10)):
            rule |= FreezeWater(i * 10) & CanLift(Weight, ["Ice"], previous_pikmin_count=i * 10)
        return rule.resolve(world)

@dataclasses.dataclass()
class CanLiftInWater(Rule["ManualWorld"], game=game_name):
    """A rule that checks if the player has enough pikmin + pup to lift an item in water"""
    Weight: int
    CloseToSurface: bool = False
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        Weight = self.Weight
        rule: Rule["ManualWorld"]
        colors = ["Blue", "Glow"]
        if self.CloseToSurface:
            colors.append("Pink")

        rule = CanLift(Weight, colors, True, 2 if self.CloseToSurface else 3)
        return rule.resolve(world)

@dataclasses.dataclass()
class CanLift(Rule["ManualWorld"], game=game_name):
    """A rule that checks if the player has enough pikmin + pup to lift an item"""
    weight: int | FieldResolver
    """How much does the item weight"""
    excluded_colors: str | list[str] = ""
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
    previous_pikmin_count: int | FieldResolver = 0
    """For things like freezing the water"""
    USE_FULL_RULES: bool = USE_FULL_RULES
    @override
    def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
        weight = resolve_field(self.weight, world, int)
        previous_pikmin_count = resolve_field(self.previous_pikmin_count, world, int)
        if weight <= 0:
            return True_().resolve(world)
        excluded_colors = self.excluded_colors
        if isinstance(excluded_colors, str):
            excluded_colors = excluded_colors.strip().split(";")
        invert_excluded = resolve_field(self.invert_excluded, world, bool)
        purple_excluded = invert_excluded
        pup_status = resolve_field(self.pup_status, world, int)
        colors = {c.removesuffix(" Real") for c in world.item_and_event_name_groups["Pikmins Carry"]}
        if invert_excluded and not excluded_colors:
            raise Exception("You inverted the excluded colors without 'including' any and thus this CanLift always return False")

        elif invert_excluded and excluded_colors:
            purple_excluded = True
            pikmins: set[str] = set()
            for color in excluded_colors:
                color = color.strip()
                if color == "Purple":
                    purple_excluded = False
                    continue
                elif color == "Pup":
                    continue
                pikmins.add(color)

        else:
            pikmins = set(colors)

            if excluded_colors:
                for color in excluded_colors:
                    color = color.strip()
                    if color == "Purple":
                        purple_excluded = True
                        continue
                    elif color == "Pup":
                        continue
                    real_name = color.strip()
                    if real_name in pikmins:
                        pikmins.remove(real_name)

        Glow_Pikmin_In_Daylight = getattr(world.options, "Glow_Pikmin_In_Daylight", GlowPikminUsable(GlowPikminUsable.default)).value
        if not Glow_Pikmin_In_Daylight and "Glow" in pikmins:
            pikmins.remove("Glow")

        return self.Resolved(
            weight=weight,
            previous_pikmin_count=previous_pikmin_count,
            purple_excluded=purple_excluded,
            pup_status=pup_status,
            valid_pikmins=tuple(pikmins),
            USE_FULL_RULES=self.USE_FULL_RULES,
            player=world.player,
            caching_enabled=getattr(world, "rule_caching_enabled", False),
        )

    @override
    def __str__(self) -> str:
        count = f", count={self.weight}" if isinstance(self.weight, FieldResolver) or self.weight > 1 else ""
        options = f", options={self.options}" if self.options else ""
        return f"{self.__class__.__name__}({count}{options})"

    class Resolved(Rule.Resolved):
        weight: int
        previous_pikmin_count: int
        purple_excluded: bool
        pup_status: int
        valid_pikmins: tuple[str, ...]
        USE_FULL_RULES: bool = USE_FULL_RULES
        skip_cache: ClassVar[bool] = True

        @override
        def _evaluate(self, state: CollectionState) -> bool:
            player = self.player
            def _has(item:str, count: int = 1) -> bool:
                return state.has(item, player, count)
            def _count(item:str) -> int:
                return state.count(item, player)
            max_pikmin = 100 - self.previous_pikmin_count
            max_pikmin_item = ceil(max_pikmin/10)
            def _clamp(item_count:int) -> int:
                return min(item_count, max_pikmin_item)
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
            if not self.purple_excluded:
                if self.USE_FULL_RULES:
                    if _has("Purple Onion") or _has("Purple Pikmin Source"):
                        purple_count = _clamp(_count("Purple Pikmins"))
                else:
                    purple_count = _clamp(_count("Purple Real"))
                to_lift -= purple_count*100
                if purple_count*100 >= to_lift: return True
            max_pikmin_item -= purple_count
            valid_pikmins = self.valid_pikmins
            if to_lift > 100 or not valid_pikmins or not max_pikmin_item: return False # if we get here then pup + purple failed

            pool: Counter[str] = Counter()
            if "Glow" in valid_pikmins: # Glow do not need Flarlics so don't check for those here
                glow_count = 0
                if self.USE_FULL_RULES:
                    if _has("Yonny"):
                        glow_count = _count("Glow Pikmins")
                else:
                    glow_count = _count("Glow Real")
                to_lift -= glow_count*10
            rough_count = ceil(to_lift/10)
            if rough_count > max_pikmin_item: return False
            flarlic_count = max(ceil((self.previous_pikmin_count + to_lift)/10) + purple_count - 2, 0)
            if not _has("Flarlic", flarlic_count): return False

            for color in valid_pikmins:
                if color == "Glow": continue
                if self.USE_FULL_RULES:
                    if _has(f"{color} Onion") or _has(f"{color} Pikmin Source"):
                        pool[color] = _count(f"{color} Pikmins")
                    else:
                        pool[color] = _count(f"{color} Real")
                if pool.total() >= rough_count: return True

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
            colors = set(self.valid_pikmins)
            if not self.purple_excluded:
                colors.add("Purple")
            for color in colors:
                if self.USE_FULL_RULES:
                    if color == "Glow":
                        items["Yonny"] = {id(self)}
                        continue
                    items[f"{color} Pikmins"] = {id(self)}
                    items[f"{color} Onion"] = {id(self)}
                    items[f"{color} Pikmin Source"] = {id(self)}
                else:
                    items[f"{color} Real"] = {id(self)}
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
                colors = set(self.valid_pikmins)
                if not self.purple_excluded:
                    colors.add("Purple")
                for color in colors:
                    if self.USE_FULL_RULES:
                        items.append(f"{color} Pikmins")
                        if color == "Glow":
                            items.append("Yonny")
                            continue
                        items.append(f"{color} Onion")
                        items.append(f"{color} Pikmin Source")
                    else:
                        items.append(f"{color} Real")
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
            pup_lift = 0
            purple_lift = 0
            purple_count = 0
            if self.pup_status:
                pup_lift = _PupToWeight(_count("Buff Learned"))
            if not self.purple_excluded:
                color = "Purple"
                if self.USE_FULL_RULES:
                    if _has(f"{color} Onion") or _has(f"{color} Pikmin Source"):
                        purple_lift = _count(f"{color} Real") * 100
                else:
                    purple_lift = _count(f"{color} Real") * 100
                purple_count = int(purple_lift / 100)

            for color in self.valid_pikmins:
                if self.USE_FULL_RULES:
                    if color == "Glow" and _has("Yonny"): # Glow do not need Flarlics so don't check for those
                        pool["Glow"] = _count("Glow Pikmins") * 10
                        continue
                    if _has(f"{color} Onion") or _has(f"{color} Pikmin Source"):
                        pool[color] = _count(f"{color} Pikmins") * 10
                else:
                    pool[color] = _count(f"{color} Real") * 10
            missing: list[str] = []
            if not self.purple_excluded and not purple_lift: missing.append("Purple")

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
            if not self.purple_excluded and purple_lift:
                found.append(f"Purple: {purple_lift}")
                if purple_count < 10:
                    missing.append(f"Purple: {10 - purple_count}")
            to_lift = self.weight - pup_lift - purple_lift
            rough_flarlic = ceil((to_lift + purple_count + self.previous_pikmin_count)/10)
            flarlic_count = max(rough_flarlic - 2 - pool["Glow"], 0)
            if not _has("Flarlic", flarlic_count):
                missing.extend(f"Flarlic: {flarlic_count - _count('Flarlic')}")
            missing.extend([color for color in self.valid_pikmins if color not in pool.keys() or pool[color] < 100])
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
            prefix: str = "Has enough" if self(state) else "Not Enough"
            suffix: str = "" if self(state) else f" from {found_str}{infix}{missing_str}"
            return f"{prefix} for {self.weight}x Lift Power ({total_str}/{self.weight}{suffix})"

        @override
        def __str__(self) -> str:
            count = f"{self.weight}x " if self.weight > 0 else ""
            Oatchi_str = "Oatchi, " if self.pup_status else ""
            paddle_needed: int = 0 if self.pup_status < 2 else  1 if self.pup_status == 2 else 3
            if paddle_needed:
                Oatchi_str += f"Doggy-Paddle Learned ({paddle_needed}), "
            sources: str = Oatchi_str
            sources += "Purple Pikmins + Onion/Source, " if not self.purple_excluded else ""
            sources += " Pikmins + Onion/Source, ".join(self.valid_pikmins)
            return f"Have enough {count}Lift Power from ({sources})"

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