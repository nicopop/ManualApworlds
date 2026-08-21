# Object classes from AP that represent different types of options that you can create
from Options import OptionError, Visibility, Option, FreeText, NumericOption, Toggle, DefaultOnToggle, Choice, TextChoice,\
    Range, NamedRange, OptionGroup, PerGameCommonOptions, OptionSet, DeathLink
# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from typing import Type, Any, cast, Counter, TYPE_CHECKING, Collection
import random
from Generate import get_choice
if TYPE_CHECKING:
    from .. import ManualWorld

####################################################################
# NOTE: At the time that options are created, Manual has no concept of the multiworld or its own world.
#       Options are defined before the world is even created.
#
# Example of creating your own option:
#
#   class MakeThePlayerOP(Toggle):
#       """Should the player be overpowered? Probably not, but you can choose for this to do... something!"""
#       display_name = "Make me OP"
#
#   options["make_op"] = MakeThePlayerOP
#
#
# Then, to see if the option is set, you can call is_option_enabled or get_option_value.
#####################################################################


# To add an option, use the before_options_defined hook below and something like this:
#   options["total_characters_to_win_with"] = TotalCharactersToWinWith
#

class RangeIsRandom(NamedRange):
    randomized: bool | tuple[int, int] = False
    special_range_names = {"randomized": -42}

    def __init__(self, value: int, randomized: bool | tuple[int, int] = False):
        super().__init__(value)
        self.randomized = randomized

    # Helper methods
    def get_randomized_range(self) -> tuple[int, int]:
        if isinstance(self.randomized, bool):
            if not self.randomized:
                return (self.value, self.value)
            return (self.range_start, self.range_end)
        return self.randomized

    @classmethod
    def is_text_rdm(cls, text: str) -> bool | tuple[str, tuple[int, int]]:
        """Return a tuple that consist of 'replace text with this' and a tuple of min and max range otherwise return `false`"""
        if text == "randomized":
            return (f"random", (cls.range_start, cls.range_end))
        return False

    @classmethod
    def from_text(cls, text: str) -> Range:
        text = text.lower()
        randomized: bool | tuple[int, int] = False
        custom = cls.is_text_rdm(text)
        if isinstance(custom, tuple):
            text = custom[0]
            randomized = custom[1]
        elif text.startswith("random"):
            if text.startswith("random-range-"):
                textsplit = text.split("-")
                try:
                    random_range = [int(textsplit[-2]), int(textsplit[-1])]
                except ValueError:
                    raise ValueError(f"Invalid random range {text} for option {cls.__name__}")
                random_range.sort()
                randomized = (random_range[0], random_range[1])
            else:
                randomized = (cls.range_start, cls.range_end)
        return cls(super().from_text(text).value, randomized)

class ChoiceIsRandom(Choice):
    randomized: bool | list[int] = False
    supports_weighting = False
    display_name = "ChoiceIsRandom"
    option_randomized = -42
    clean_values: None|dict = None

    def __init__(self, value: int, randomized: bool | list[int] = False):
        super().__init__(value)
        self.randomized = randomized

    # Helper methods
    def get_randomized_values(self) -> list[int]:
        if isinstance(self.randomized, bool):
            if not self.randomized:
                return [self.value]
            return list(self.get_clean_values().keys())
        return self._convert_str_list_to_int_list(self.randomized)

    @classmethod
    def get_rdm_option_name(cls) -> str:
        """Get the string representation of the "random" option value name"""
        return cls.name_lookup[-42].removeprefix("option_")

    @classmethod
    def remove_random_pick(cls, data: dict[int, str]) -> dict[int, str]:
        """Return the `data` dict with all its identified "random" values removed"""
        return {i: v for i, v in data.items() if not cls.is_str_random(v, return_list=False)}

    @classmethod
    def get_clean_values(cls) -> dict[int, str]:
        """Return original `cls.name_lookup` minus any random based option values"""
        if cls.clean_values is None:
            cls.clean_values = cls.remove_random_pick(cls.name_lookup)
        return cls.clean_values

    # Randomization detections methods grouped here for easy modification later
    @classmethod
    def is_str_random(cls, input: str, return_list = True) -> bool | list[int]:
        """Returns a `list[int]` of possible values if input is a known random, `True` if unknown and `False` if not random"""
        if input == cls.get_rdm_option_name():
            return list(cls.get_clean_values()) if return_list else True
        else:
            return input.startswith("random")

    @classmethod
    def is_random_in_list(cls, collection: Collection[str]) -> bool:
        """Are any of the values in the collection detected as "random" """
        return any(v for v in collection if cls.is_str_random(v))

    @classmethod
    def _convert_str_list_to_int_list(cls, data: list) -> list[int]:
        if isinstance(data[0], int):
            return cast(list[int], data)
        data_str = cast(list[str], data)
        return [cls.options[k] for k in data_str]
    # Standard Option methods
    @classmethod
    def from_text(cls, text: str) -> Choice:
        values = cls.is_str_random(text)
        if isinstance(values, list):
            return cls(random.choice(list(values)), values)
        elif values:
            return cls(super().from_text(text).value, True)
        else:
            return super().from_text(text)
    @classmethod
    def from_any(cls, data: Any) -> Choice:
        if type(data) is str:
            return cls.from_text(data)
        elif type(data) is int:
            return cls.from_text(cls.name_lookup[data])
        elif type(data) is dict or type(data) is list:
            if type(data) is list:
                data = Counter({v:50 for v in data})
            else:
                data = +Counter(data) # remove all zero values
            counter: Counter[str] = Counter(data)
            randomized: bool|list[int] = []

            for key, value in Counter(counter).items():
                ret = cls.is_str_random(key)
                if isinstance(ret, list):
                    for v in ret:
                        name = cls.name_lookup[v]
                        if name not in counter.keys():
                            counter[name] = value
                    del counter[key]
                elif ret:
                    counter = Counter({v: (value if v not in counter.keys() else counter[v]) for v in cls.get_clean_values().values()})
                    break

            if len(counter) > 1:
                randomized = cls._convert_str_list_to_int_list(list(counter.keys()))
            else:
                randomized = False
            name = cast(str, get_choice(cls.display_name, {cls.display_name: dict(counter)}))

            return cls(int(super().from_text(name)), randomized)

        return super().from_any(data)

class ToggleIsRandom(ChoiceIsRandom):
    display_name = "ToggleIsRandom"
    option_false = 0
    option_true = 1

    @classmethod
    def from_text(cls, text: str) -> Choice:
        if cls.is_str_random(text):
            return cls(random.choice([0,1]), [0,1])
        elif text.lower() in {"off", "0", "false", "none", "null", "no", "disabled"}:
            return cls(0)
        elif text.lower() in {"on", "1", "true", "yes", "enabled"}:
            return cls(1)
        else:
            raise OptionError(f"Option {cls.__name__} does not support a value of {text}")

    @classmethod
    def get_option_name(cls, value):
        return {0: "No", 1: "Yes", -42: cls.get_rdm_option_name().capitalize()}[int(value)]
class DefaultOnToggleIsRandom(ToggleIsRandom):
    default = 1

class EvilBiomeType(ChoiceIsRandom):
    """Choose which type of Evil biome will be in your game"""
    option_corruption = 1
    option_crimson = 2
    option_both = 3
    option_random_1 = -41
    default = -41

    @classmethod
    def is_str_random(cls, input: str, return_list = True) -> bool | list[int]:
        """Returns a `list[int]` of possible values if input is a known random, `True` if unknown and `False` if not random"""
        # override here for the random_1
        if input == "random_1":
            return [cls.option_corruption, cls.option_crimson] if return_list else True
        else:
            return super().is_str_random(input, return_list)

class BiomeRdmSeed(TextChoice):
    """If set to anything other than default aka 0, the value will be used for the biome seed"""
    option_default = 0
    default = 0

class ObjectivesTypesForGoal(RangeIsRandom):
    """How many Objectives Types will you need to finish before you can goal"""
    default = 1
    special_range_names = RangeIsRandom.special_range_names | {"default": default}
    range_start = 0
    range_end = 4

# from ..Items import item_name_to_item
# from ..Game import filler_item_name
# removable_items = {n for n, item in item_name_to_item.items() if item.get("removable", True) and not item.get("disabled")}
# if filler_item_name in removable_items:
#     removable_items.remove(filler_item_name)
# class RemoveItems(OptionSet):
#     """WARNING CAN BREAK GENERATION: Specified items will be removed from the pool but not logic"""
#     display_name = "Remove Items"
#     valid_keys =  removable_items
#     visibility = Visibility.complex_ui | Visibility.spoiler

# from ..Locations import location_name_to_location
# removable_locations = {n for n, location in location_name_to_location.items() if location.get("removable", True) \
#     and not location.get("disabled") and not location.get("create_event") and not location.get("victory") \
#     and not set(location.get("category", [])).intersection(["do_launch_codes", "no_launch_codes", "do_place_item_category", "no_place_item_category"])}
# class RemoveLocation(OptionSet):
#     """WARNING CAN BREAK GENERATION: Specified locations will be removed from the world"""
#     display_name = "Remove Locations"
#     valid_keys = removable_locations
#     visibility = Visibility.complex_ui | Visibility.spoiler


# This is called before any manual options are defined, in case you want to define your own with a clean slate or let Manual define over them
def before_options_defined(options: dict[str, Type[Option[Any]]]) -> dict[str, Type[Option[Any]]]:
    options["evil_biome"] = EvilBiomeType
    options["biome_seed"] = BiomeRdmSeed
    options["goal_objectives"] = ObjectivesTypesForGoal


    # options["remove_items"] = RemoveItems
    # options["remove_locations"] = RemoveLocation
    return options

# This is called after any manual options are defined, in case you want to see what options are defined or want to modify the defined options
def after_options_defined(options: Type[PerGameCommonOptions]):
    # To access a modifiable version of options check the dict in options.type_hints
    # For example if you want to change DLC_enabled's display name you would do:
    # options.type_hints["DLC_enabled"].display_name = "New Display Name"

    #  Here's an example on how to add your aliases to the generated goal
    # options.type_hints['goal'].aliases.update({"example": 0, "second_alias": 1})
    # options.type_hints['goal'].options.update({"example": 0, "second_alias": 1})  #for an alias to be valid it must also be in options
    # goal_gen_options = dict(options.type_hints['goal'].options)
    # goal_gen_name_lookup = dict(options.type_hints['goal'].name_lookup)
    # goal_gen_options_names = {a:v for a,v in dict(options.type_hints['goal'].__dict__).items() if a.startswith("option_")}
    # for option, value in goal_gen_options_names.items():
    #     setattr(Goal, option, value)
    # options.type_hints['goal'] = Goal
    # options.type_hints['goal'].name_lookup.update(goal_gen_name_lookup)
    # options.type_hints['goal'].options.update(goal_gen_options)
    # options.type_hints['filler_traps'].range_end = 75
    # options.type_hints['filler_traps'].default = 20
    options.type_hints['death_link'].__doc__ = DeathLink.__doc__
    pass

# Use this Hook if you want to add your Option to an Option group (existing or not)
def before_option_groups_created(groups: dict[str, list[Type[Option[Any]]]]) -> dict[str, list[Type[Option[Any]]]]:
    # Uses the format groups['GroupName'] = [TotalCharactersToWinWith]
    return groups

def after_option_groups_created(groups: list[OptionGroup]) -> list[OptionGroup]:
    # for group in groups:
    #     if group.name == 'Item & Location Options':
    #         group.options.extend([RemoveItems, RemoveLocation])
    return groups
