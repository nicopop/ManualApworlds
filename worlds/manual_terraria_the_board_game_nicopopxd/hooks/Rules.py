from typing import Optional, TYPE_CHECKING, cast, Any
from worlds.AutoWorld import World
from ..Helpers import clamp, get_items_with_value, is_item_name_enabled
from ..Game import game_name
from BaseClasses import MultiWorld, CollectionState

import dataclasses
from Utils import version_tuple
use_rulebuilder = version_tuple >= (0, 6, 7)

if TYPE_CHECKING:
    from .. import ManualWorld

# Sometimes you have a requirement that is just too messy or repetitive to write out with boolean logic.
# Define a function here, and you can use it in a requires string with {function_name()}.
def overfishedAnywhere(world: World, state: CollectionState, player: int):
    """Has the player collected all fish from any fishing log?"""
    for cat, items in world.item_name_groups.items():
        if cat.endswith("Fishing Log") and state.has_all(items, player):
            return True
    return False

# You can also pass an argument to your function, like {function_name(15)}
# Note that all arguments are strings, so you'll need to convert them to ints if you want to do math.
def anyClassLevel(state: CollectionState, player: int, level: str):
    """Has the player reached the given level in any class?"""
    for item in ["Figher Level", "Black Belt Level", "Thief Level", "Red Mage Level", "White Mage Level", "Black Mage Level"]:
        if state.count(item, player) >= int(level):
            return True
    return False

# You can also return a string from your function, and it will be evaluated as a requires string.
def requiresMelee():
    """Returns a requires string that checks if the player has unlocked the tank."""
    return "|Figher Level:15| or |Black Belt Level:15| or |Thief Level:15|"

def Event(location: str, count: int = 1) -> str:
    event_name = f"|[Event] {location.strip()}:{count}|"
    return event_name

def Discover(biome: str, world: "ManualWorld") -> str:
    biomes: list[str] = world.biomes_order
    if not is_item_name_enabled(world.multiworld, world.player, "Progressive Biome") or biome not in biomes:
        return "1"
    index = biomes.index(biome)
    required = 3 - index if index < 3 else index - 1
    return f"|Progressive Biome:{required}|"

def DiscoverRule(biome: str, world: "ManualWorld") -> str:
    value = Discover(biome, world)
    if value == "1":
        return ""
    return value

# A rule that checks if the player has at least count of the given items, ignoring duplicates of the same item
def HasFromCategoryUnique(category: str, count: str, state: CollectionState, world: "ManualWorld", player: int) -> bool:
    requested_count = int(count.strip())
    return state.has_from_list_unique(world.item_and_event_name_groups[category], player, requested_count)

def GoalObjectives(state: CollectionState, world: "ManualWorld", player: int,) -> bool:
    from .Options import ObjectivesTypesForGoal
    objectives = cast(ObjectivesTypesForGoal, world.options.goal_objectives) # type: ignore
    requested_count = objectives.value
    return HasFromCategoryUnique("Objectives Final", str(requested_count), state=state, world=world, player=player)

if use_rulebuilder:
    from rule_builder.rules import HasFromListUnique, Rule
    @dataclasses.dataclass()
    class HasFromCategoryUniqueRule(Rule["ManualWorld"], game=game_name):
        category: str
        count: str
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            requested_count = int(self.count.strip())
            requested_list = world.item_and_event_name_groups[self.category.strip()]
            return HasFromListUnique(*requested_list, count=requested_count).resolve(world)

    @dataclasses.dataclass()
    class GoalObjectivesRule(Rule["ManualWorld"], game=game_name):
        def _instantiate(self, world: "ManualWorld") -> Rule.Resolved:
            from .Options import ObjectivesTypesForGoal
            objectives = cast(ObjectivesTypesForGoal, world.options.goal_objectives) # type: ignore
            requested_count = objectives.value
            return HasFromCategoryUniqueRule("Objectives Final", str(requested_count)).resolve(world)


# def GoalPlus(world: "ManualWorld") -> str:
#     from .Options import Goal
#     needed = []
#     if world.options.require_solanum.value:
#         needed.append(Event("6 - Travel"))
#     if world.options.require_prisoner.value and world.options.goal.value != Goal.alias_prisoner:
#         needed.append(Event("9D - Vault"))
#     return " and ".join(needed) or "1"

# def GoalPlusRule(world: "ManualWorld") -> str:
#     value = GoalPlus(world)
#     if value == "1":
#         return ""
#     return value
