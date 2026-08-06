from BaseClasses import Tutorial
from typing import Any, cast
from worlds.AutoWorld import World, WebWorld

_location_table: list[dict[str, Any]] = []
_item_table: list[dict[str, Any]] = []

def load_manifest() -> dict[str, Any]:
    import json, pkgutil
    try:
        file = pkgutil.get_data(__name__, "archipelago.json")
        if file is not None:
            filedata = json.loads(file.decode())
        else:
            filedata = {}
    except:
        filedata = {}

    return filedata

_manifest: dict[str, Any] = load_manifest()

# called after the game.json file has been loaded
def after_load_game_file(game_table: dict) -> dict:
    return game_table

# called after the items.json file has been loaded, before any item loading or processing has occurred
# if you need access to the items after processing to add ids, etc., you should use the hooks in World.py
def after_load_item_file(item_table: list) -> list:
    global _item_table
    _item_table = item_table
    return item_table


# called after the locations.json file has been loaded, before any location loading or processing has occurred
# if you need access to the locations after processing to add ids, etc., you should use the hooks in World.py
def after_load_location_file(location_table: list[dict[str, Any]]) -> list:
    global _location_table
    _location_table = location_table
    return location_table

# called after the events.json file has been loaded, before any processing has occurred
# If you need access to the events after processing, you should use the hooks in World.py
def after_load_event_file(event_table: list) -> list:
    class event_override():
        name: str
        data: dict[str, Any]

        def __init__(self, name: str, data = {}) -> None:
            if name.startswith("@"):
                name = f"[Event] {name.removeprefix('@')}"
            self.name = name
            self.data = data
            pass

    for location in _location_table:
        event_requested = location.get("create_event")
        if not event_requested:
            continue

        base_event_override = {}
        if (visible := location.get("event_visible")) is not None:
            base_event_override["visible"] = visible
        if (categories := location.get("event_category")) is not None:
            base_event_override["category"] = categories

        if isinstance(event_requested, str):
            events_to_make = [event_override(event_requested, base_event_override)]
        elif isinstance(event_requested, list):
            events_to_make = []
            for i in event_requested:
                if isinstance(i, str):
                    events_to_make.append(event_override(i, base_event_override))
                elif isinstance(i, dict):
                    name = i.pop("name")
                    events_to_make.append(event_override(name, base_event_override | i))
                else:
                    raise ValueError("uh what...")
        else:
            events_to_make = [event_override(f"@{location['name']}", base_event_override)]

        for event_obj in events_to_make:
            event ={"name": event_obj.name, "copy_location": location["name"]} | event_obj.data

            event_table.append(event)
    return event_table
# called after the regions.json file has been loaded, before any location loading or processing has occurred
# if you need access to the locations after processing to add ids, etc., you should use the hooks in World.py
def after_load_region_file(region_table: dict) -> dict:
    return region_table

# called after the categories.json file has been loaded
def after_load_category_file(category_table: dict[str, Any]) -> dict:
    for obj in _item_table + _location_table:
        if obj.get("old_name"):
            old_name: str|list[str] = obj["old_name"]
            if not isinstance(old_name, list):
                old_name = [old_name]
            for name in old_name:
                if not obj.get("category"):
                    obj["category"] = []
                obj["category"].append(name)
                if name not in category_table.keys():
                    category_table[name] = {"hidden": True}
    return category_table

# called after the categories.json file has been loaded
def after_load_option_file(option_table: dict) -> dict:
    # option_table["core"] is the dictionary of modification of existing options
    # option_table["user"] is the dictionary of custom options
    return option_table

# called after the meta.json file has been loaded and just before the properties of the apworld are defined. You can use this hook to change what is displayed on the webhost
# for more info check https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/world%20api.md#webworld-class
def after_load_meta_file(meta_table: dict) -> dict:
    if not meta_table.get("docs"):
        meta_table['docs'] = {}
    if not meta_table['docs'].get("web"):
        meta_table['docs']['web'] = {}

    meta_table["docs"]["apworld_description"] = f"""
    Manual games allow you to set custom check locations and custom item names that will be rolled into a multiworld.
    In this case a board game released in 2026: Terraria: The Board Game
    the player must manually refrain from using these gathered items until the tracker shows that they have been acquired or sent.
    [Apworld Version: {_manifest.get('world_version', 'Unknown')}]
    """
    web = meta_table['docs']['web']
    # web['options_presets'] = {
    #     "Short":{
    #         "goal": "standard"
    #     },
    #     "Long":{
    #         "require_solanum": True,
    #         "require_prisoner": True,
    #         "do_place_item_category": False,
    #         "goal": "standard"
    #     }
    # }
    web['theme'] = "ocean"
    web['bug_report_page'] = "https://discord.com/channels/1097532591650910289/1495111996150906880"

    return meta_table
