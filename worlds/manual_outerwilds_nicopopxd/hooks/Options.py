# Object classes from AP that represent different types of options that you can create
from Options import Visibility, Option, FreeText, NumericOption, Toggle, DefaultOnToggle, Choice, TextChoice, Range, NamedRange, OptionGroup, PerGameCommonOptions
# These helper methods allow you to determine if an option has been set, or what its value is, for any player in the multiworld
from typing import Type, Any, cast, Counter, TYPE_CHECKING

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
#class TotalCharactersToWinWith(Range):
#    """Instead of having to beat the game with all characters, you can limit locations to a subset of character victory locations."""
#    display_name = "Number of characters to beat the game with before victory"
#    range_start = 10
#    range_end = 50
#    default = 50
class ChoiceIsRandom(Choice):
    randomized: bool | list[str] = False
    supports_weighting = False
    display_name = "ChoiceIsRandom"

    def __init__(self, value: int, randomized: bool | list[str] = False):
        super().__init__(value)
        self.randomized = randomized

    @classmethod
    def from_text(cls, text: str) -> Choice:
        if text == "random":
            ret = super().from_text(text)
            return cls(int(ret), True)
        else:
            return super().from_text(text)
    @classmethod
    def from_any(cls, data: Any) -> Choice:
        from Generate import get_choice
        if type(data) is str:
            return cls.from_text(data)
        elif type(data) is dict:
            filtered = +Counter(data) # remove all zero values
            randomized: bool|list = False
            ret = cast(str, get_choice(cls.display_name, {cls.display_name: dict(filtered)}))
            if ret == "random":
                randomized = True
            elif len(filtered) > 1:
                if "random" in filtered.keys():
                    randomized = True
                else:
                    randomized = list(filtered.keys())
            return cls(int(cls.from_text(ret)), randomized)
        elif type(data) is list:
            randomized = False
            ret = cast(str, get_choice(cls.display_name, {cls.display_name: data}))
            if ret == "random":
                randomized = True
            elif len(data) > 1:
                if "random" in data:
                    randomized = True
                else:
                    randomized = data
            return cls(int(cls.from_text(ret)), randomized)
        return super().from_any(data)

class ToggleIsRandom(Toggle):
    randomized: bool = False
    supports_weighting = False
    display_name = "ToggleIsRandom"
    def __init__(self, value: int, randomized: bool = False):
        super().__init__(value)
        self.randomized = randomized

    @classmethod
    def from_text(cls, text: str) -> Toggle:
        if text == "random":
            ret = super().from_text(text)
            return cls(int(ret), True)
        else:
            return super().from_text(text)
    @classmethod
    def from_any(cls, data: Any) -> Toggle:
        from Generate import get_choice
        if type(data) is str:
            return cls.from_text(data)
        elif type(data) is dict:
            filtered = +Counter(data) # remove all zero values
            randomized = False
            ret = cast(str, get_choice(cls.display_name, {cls.display_name: dict(filtered)}))
            if ret == "random" or len(filtered.keys()) > 1:
                randomized = True
            return cls(int(cls.from_text(ret)), randomized)
        return super().from_any(data)

class DefaultOnToggleIsRandom(ToggleIsRandom):
    default = 1


class RequireSolanum(ToggleIsRandom):
    """Do you want to require Talking to Solanum before you can win?"""
    display_name = "Require Talking to Solanum"

class RequirePrisoner(ToggleIsRandom):
    """Do you want to require Talking to the Prisoner before you can win?"""
    automatically_disabled = False
    display_name = "Require Talking to the Prisoner"
class do_spooks(DefaultOnToggle):
    """Do you want to enable some of the Spookier DLC locations?"""
    display_name = "ReduceSpooks"
class MainDlcKnowledge(Toggle):
    """Should The main 2 dlc Progression items (stranger access and dreamworld access) be enabled?
    AKA lock going to the Stranger and the Dream behind an "access" mcguffin item each
    """
    display_name = "Enable Main 2 Dlc Access Items"

class LocalPlacedItems(DefaultOnToggle):
    """Do you want some items to be predetermined to help with the flow of the game"""#todo find a better way to phrase this
    display_name = "Predetermined Local Items"

class ShuffleSpacesuit(ToggleIsRandom):
    """Puts the spacesuit into the Archipelago item pool, forcing you to play suitless until it's found.
    This is a HIGHLY EXPERIMENTAL setting. Expect logic bugs. Feedback encouraged."""
    display_name = "Shuffle SpaceSuit"

# class ShipKey(DefaultOnToggle):
#     """Lock being able to move the ship behind this item, you still can grab the SpaceSuit and use it's jetpack but you can't take off with the ship"""
#     display_name = "Ship Key Logic"

class EarlyShipKey(Choice):
    """Do you want the Ship Key to be located in the early game
    Leave it as startswith to disable the Ship Key logic"""
    display_name = "Ship Key Logic"
    option_local_early = 0
    option_local_anywhere = 1
    option_global_early = 2
    alias_global = option_global_early
    option_global_anywhere = 3
    option_startswith = 4
    default = 4

class RandomizeDLC(DefaultOnToggleIsRandom):
    """Should the dlc location and items be enabled"""
    display_name = "Randomize DLC"

class RandomizeBaseGame(DefaultOnToggleIsRandom):
    """Should the base location and items be enabled
    If an location/item is required for you goal it will be enabled"""
    display_name = "Randomize Base Game"

class RandomizeMod1(ToggleIsRandom):
    """Should locations and item from mod X be enabled"""
    display_name = "Randomize Mod X"
    visibility = Visibility.none

class BiggerSphere1(Toggle):
    """when true remove the launch codes logic so Sphere 1 is bigger
    You will still need to talk to Hornfels to start the loop"""
    display_name = "Remove Launch codes"

class ReverseTeleporter(Toggle):
    """Turn this on if you want and use a mod to enable reverse teleporters,
    Warning No such mod exist as of writing this, and thus the logic is untested"""
    display_name = "Enable Reverse Teleporters Logic"
    visibility = Visibility.none

class Goal(ChoiceIsRandom):
    """Where do you want to end,
    standard(default): for dlc only will end on prisoner, for base and base+dlc will end at the eye.
    Vanilla% aka eye: Will require going to the eye.
    Prisoner% aka prisoner: Will end after talking to the prisoner
    GhostsInTheMachine% aka visit_all_archive: Will End by visiting all the archive in a single loop without being caught
    BreakSpaceTimeInATP% aka ash_twin_project_break_spacetime: Require going to the ash twin project and break spacetime there.
    BreakSpaceTimeInLab% aka high_energy_lab_break_spacetime: Require going to the high energy lab and break spacetime there.
    QuantumStuck% aka stuck_with_solanum: Get the Adv. warp core to Solanum and wait for Credits.
    StrangerStuck% aka stuck_in_stranger: Get the Adv. warp core to the Stranger and wait for Credits.
    DreamStuck% aka stuck_in_dream: Get the Adv. warp core to the Stranger and die to get to the Dreamworld.
    """
    display_name = "Goal"
    alias_standard = 0
    alias_vanilla = 1
    alias_prisoner = 2
    alias_visit_all_archive = 3
    alias_ash_twin_project_break_spacetime = 4
    alias_high_energy_lab_break_spacetime = 5
    alias_stuck_with_solanum = 6
    alias_stuck_in_stranger = 7
    alias_stuck_in_dream = 8
    default = 0

    dlc_options = [alias_prisoner, alias_visit_all_archive, alias_stuck_in_stranger, alias_stuck_in_dream]

    def isValueInDLC(self) -> bool:
        return self.isThisValueInDLC(self.value)

    @classmethod
    def isThisValueInDLC(cls, value) -> bool:
        return value in cls.dlc_options

    def getRDMvalue(self, world: "ManualWorld", filter_dlc = False) -> int|None:
        randoms = self.randomized

        if isinstance(randoms, bool):
            randoms = list(self.name_lookup.values())

        if filter_dlc:
            randoms = cast(list[str], [o for o in randoms if self.options.get(o) and self.options[o] not in self.dlc_options])

        if not randoms:
            return None
        return self.options[world.random.choice(randoms)]

class ApWorldVersion(FreeText):
    """Do not change this, it will get set to the apworld version"""
    display_name = "Game Version (Detected)"
    default = "Should Be Detected"
    visibility = Visibility.spoiler

# This is called before any manual options are defined, in case you want to define your own with a clean slate or let Manual define over them
def before_options_defined(options: dict[str, Type[Option[Any]]]) -> dict[str, Type[Option[Any]]]:
#    options["total_characters_to_win_with"] = TotalCharactersToWinWith
    options["game_version"] = ApWorldVersion
    options["require_solanum"] = RequireSolanum
    options["require_prisoner"] = RequirePrisoner
    options["enable_spooks"] = do_spooks
    options["remove_launch_codes"] = BiggerSphere1
    options["ship_key_logic"] = EarlyShipKey
    options["shuffle_spacesuit"] = ShuffleSpacesuit
    options["do_place_item_category"] = LocalPlacedItems
    # ptions["randomized_content"] = RandomContent
    options["randomize_base_game"] = RandomizeBaseGame
    options["randomize_dlc"] = RandomizeDLC
    options["dlc_access_items"] = MainDlcKnowledge
    options["reverse_teleporters"] = ReverseTeleporter
    return options

# This is called after any manual options are defined, in case you want to see what options are defined or want to modify the defined options
def after_options_defined(options: Type[PerGameCommonOptions]):
    # To access a modifiable version of options check the dict in options.type_hints
    # For example if you want to change DLC_enabled's display name you would do:
    # options.type_hints["DLC_enabled"].display_name = "New Display Name"

    #  Here's an example on how to add your aliases to the generated goal
    # options.type_hints['goal'].aliases.update({"example": 0, "second_alias": 1})
    # options.type_hints['goal'].options.update({"example": 0, "second_alias": 1})  #for an alias to be valid it must also be in options
    goal_gen_options = dict(options.type_hints['goal'].options)
    goal_gen_name_lookup = dict(options.type_hints['goal'].name_lookup)
    goal_gen_options_names = {a:v for a,v in dict(options.type_hints['goal'].__dict__).items() if a.startswith("option_")}
    for option, value in goal_gen_options_names.items():
        setattr(Goal, option, value)
    options.type_hints['goal'] = Goal
    options.type_hints['goal'].name_lookup = goal_gen_name_lookup
    options.type_hints['goal'].options.update(goal_gen_options)
    options.type_hints['filler_traps'].range_end = 75
    options.type_hints['filler_traps'].default = 20

    # generated_goal = options.type_hints.get('goal', {})
    # if generated_goal and issubclass(your_goal_class, Choice) and not issubclass(type(generated_goal), your_goal_class):
    #     goals = {'option_' + i: v for i, v in generated_goal.options.items() if i != 'default'}
    #     for option, value in your_goal_class.options.items():
    #         if option == 'default':
    #             continue
    #         goals[f"alias_{option}"] = value
    #     options['goal'] = type('goal', (Choice,), goals)
    #     options['goal'].default = your_goal_class.options.get('default', generated_goal.default)
    #     options['goal'].__doc__ = your_goal_class.__doc__ or options['goal'].__doc__
    # return options

# Use this Hook if you want to add your Option to an Option group (existing or not)
def before_option_groups_created(groups: dict[str, list[Type[Option[Any]]]]) -> dict[str, list[Type[Option[Any]]]]:
    # Uses the format groups['GroupName'] = [TotalCharactersToWinWith]
    return groups

def after_option_groups_created(groups: list[OptionGroup]) -> list[OptionGroup]:
    return groups
