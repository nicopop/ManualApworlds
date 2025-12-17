# Object classes from AP core, to represent an entire MultiWorld and this individual World that's part of it
from BaseClasses import MultiWorld, CollectionState, Item, ItemClassification
from worlds.AutoWorld import World
from typing import TYPE_CHECKING, cast, Any
from math import ceil

import logging
import re, inspect

# Object classes from Manual -- extending AP core -- representing items and locations that are used in generation
from .. import Rules
from ..Helpers import remove_specific_item, convert_string_to_type, clamp
from ..Rules import infix_to_postfix, evaluate_postfix
from . import Rules as Hooks_Rules

if TYPE_CHECKING:
    from .. import ManualWorld

def convert_req_function_args(state: CollectionState, multiworld: MultiWorld, player: int, func, args: list[Any], areaName: str):
    """Taken straight out of Rules.py with slight modifications"""
    world = multiworld.worlds[player]
    parameters = inspect.signature(func).parameters
    knownParameters = [World, 'ManualWorld', MultiWorld, CollectionState]
    index = -1
    for parameter in parameters.values():
        target_type = parameter.annotation
        index += 1
        if target_type in knownParameters:
            if target_type in [World, 'ManualWorld']:
                args.insert(index, world)
            elif target_type == MultiWorld:
                args.insert(index, multiworld)
            elif target_type == CollectionState:
                args.insert(index, state)
            continue
        if parameter.name.lower() == "player":
            args.insert(index, player)
            continue

        if index < len(args) and args[index] != "":
            value = args[index].strip()
        else:
            if parameter.default is not inspect.Parameter.empty:
                if index < len(args):
                    args[index] = parameter.default
                else:
                    args.insert(index, parameter.default)
                continue
            else:
                if parameter.annotation is inspect.Parameter.empty:
                    raise Exception(f"A call of the \"{func.__name__}\" function in \"{areaName}\"'s requirement, asks for a value for its argument \"{parameter.name}\" but it's missing.")
                else:
                    raise Exception(f"A call of the \"{func.__name__}\" function in \"{areaName}\"'s requirement, asks for a value of type {target_type} for its argument \"{parameter.name}\" but it's missing.")

        if target_type == str or parameter.annotation is inspect.Parameter.empty: #Don't convert since its already a string or if we don't know the type to convert to
            args[index] = value
            continue

        try:
            value = convert_string_to_type(value, target_type)

        except Exception as e:
            raise Exception(f"A call of the \"{func.__name__}\" function in \"{areaName}\"'s requirement, asks for a value of type {target_type}\nfor its argument \"{parameter.name}\" but its value \"{value}\" cannot be converted to {target_type} \nOriginal Error:'{e}'")

        args[index] = value

def check_area(state: CollectionState, multiworld: MultiWorld, player: int, area: dict) -> bool:
    """checkRequireStringForArea taken straight out of Rules.py with slight modifications"""
    world = cast("ManualWorld", multiworld.worlds[player])
    requires_list = cast(str,area.get("requires", ""))

    # Get the "real" item counts of item in the pool/placed/starting_items
    items_counts = world.get_item_counts(player, only_progression=True)

    # Preparing some variables for exception messages
    area_type = "region" if area.get("is_region",False) else "location"
    area_name = area.get("name", f"unknown with these parameters: {area}")

    if requires_list == "":
        return True

    def findAndRecursivelyExecuteFunctions(requires_list: str, recursionDepth: int = 0) -> str:
        found_functions = re.findall(r'\{(\w+)\((.*?)\)\}', requires_list)
        if found_functions:
            if recursionDepth > world.rules_functions_maximum_recursion:
                raise RecursionError(f'One or more functions in {area_type} "{area_name}"\'s requires looped too many time (maximum recursion is {world.rules_functions_maximum_recursion}) \
                                        \n    As of this Exception the following function(s) are waiting to run: {[f[0] for f in found_functions]} \
                                        \n    And the currently processed requires look like this: "{requires_list}"')
            else:
                for item in found_functions:
                    func_name = item[0]
                    func_args = item[1].split(",")
                    if func_args == ['']:
                        func_args.pop()

                    func = getattr(Rules, func_name, None)

                    if func is None:
                        func = getattr(Hooks_Rules, func_name, None)

                    if not callable(func):
                        raise ValueError(f'Invalid function "{func_name}" in {area_type} "{area_name}".')

                    convert_req_function_args(state, multiworld, player, func, func_args, area_name)
                    try:
                        result = func(*func_args)
                    except Exception as ex:
                        raise RuntimeError(f'A call to the function "{func_name}" in {area_type} "{area_name}"\'s requires raised an Exception. \
                                            \nUnless it was called by another function, it should look something like "{{{func_name}({item[1]})}}" in {area_type}s.json. \
                                            \nFull error message: \
                                            \n\n{type(ex).__name__}: {ex}')
                    if isinstance(result, bool):
                        requires_list = requires_list.replace("{" + func_name + "(" + item[1] + ")}", "1" if result else "0")
                    else:
                        requires_list = requires_list.replace("{" + func_name + "(" + item[1] + ")}", str(result))

            requires_list = findAndRecursivelyExecuteFunctions(requires_list, recursionDepth + 1)
        return requires_list

    requires_list = findAndRecursivelyExecuteFunctions(requires_list)

    # parse user written statement into list of each item
    for item in re.findall(r'\|[^|]+\|', requires_list):
        require_category = False

        if '|@' in item:
            require_category = True

        item_base = item
        item = item.lstrip('|@$').rstrip('|')

        item_parts = item.split(":")  # type: list[str]
        item_name = item
        item_count = "1"


        if len(item_parts) > 1:
            item_name = item_parts[0].strip()
            item_count = item_parts[1].strip()

        total = 0

        if require_category:
            category_items = [item for item in world.item_name_to_item.values() if "category" in item and item_name in item["category"]]
            category_items_counts = sum([items_counts.get(category_item["name"], 0) for category_item in category_items])
            if item_count.lower() == 'all':
                item_count = category_items_counts
            elif item_count.lower() == 'half':
                item_count = int(category_items_counts / 2)
            elif item_count.endswith('%') and len(item_count) > 1:
                percent = clamp(float(item_count[:-1]) / 100, 0, 1)
                item_count = ceil(category_items_counts * percent)
            else:
                try:
                    item_count = int(item_count)
                except ValueError as e:
                    raise ValueError(f"Invalid item count `{item_name}` in {area}.") from e

            for category_item in category_items:
                total += state.count(category_item["name"], player)

                if total >= item_count:
                    requires_list = requires_list.replace(item_base, "1")
        else:
            item_current_count = items_counts.get(item_name, 0)
            if item_count.lower() == 'all':
                item_count = item_current_count
            elif item_count.lower() == 'half':
                item_count = int(item_current_count / 2)
            elif item_count.endswith('%') and len(item_count) > 1:
                percent = clamp(float(item_count[:-1]) / 100, 0, 1)
                item_count = ceil(item_current_count * percent)
            else:
                item_count = int(item_count)

            total = state.count(item_name, player)

            if total >= item_count:
                requires_list = requires_list.replace(item_base, "1")

        if total <= item_count:
            requires_list = requires_list.replace(item_base, "0")
    requires_list = re.sub(r'\s?\bAND\b\s?', '&', requires_list, count=0, flags=re.IGNORECASE)
    requires_list = re.sub(r'\s?\bOR\b\s?', '|', requires_list, count=0, flags=re.IGNORECASE)

    requires_string = infix_to_postfix("".join(requires_list), area)
    return (evaluate_postfix(requires_string, area)) # pyright: ignore[reportArgumentType]
