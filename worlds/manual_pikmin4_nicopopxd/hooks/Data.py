from BaseClasses import Tutorial, Location
from typing import Any, cast
from worlds.AutoWorld import World, WebWorld

import logging
# region create_event
# this part is required for create_event
_location_table: list[dict[str, Any]] = []
# endregion

# region load extra files
class metadata_class():
    extra_files: list[str]
    ids_reserved: int

    def __init__(self, json: dict[str, Any], offset_size: int = 1000):
        self.extra_files = json.get("extra_files", [])
        self.ids_reserved = json.get("offset", offset_size)
def recursively_find_files_to_load(data_table: list[dict[str, Any]]|dict[str, Any], offset: int = 0, offset_size: int = 1000, adjust_ids: bool = True) -> tuple[int, int]:
    from ..Helpers import load_data_file
    errors: list[str] = []
    if isinstance(data_table, dict): # things like region files
        current_offset, last_offset_size = 0, 0
        if data_table:
            FileMetaData = data_table.pop("FileMetaData", "")
            if FileMetaData:
                metadata = metadata_class(FileMetaData, 0)
            else:
                return 0, 0
        else:
            return 0, 0
        for extra_file in metadata.extra_files:
            new_dict_table: dict[str, Any] = load_data_file(extra_file)
            new_dict_table.pop("$schema", "")
            recursively_find_files_to_load(new_dict_table)
            shared_keys = list(data_table.keys() & new_dict_table.keys())
            nl = "\n"
            if shared_keys:
                errors.append(f'file {extra_file} contains {len(shared_keys)} key{"s" if len(shared_keys) > 1 else ""} that are shared with existing tables' +
                              f"{nl} Here's the list of those duplicate: [{', '.join(shared_keys)}]")

            else:
                data_table |= new_dict_table

    else: # lists of dicts like locations.json
        if data_table:
            if data_table[0].get("name", "") == "FileMetaData":
                metadata = metadata_class(data_table.pop(0), offset_size)
            elif data_table[0].get("FileMetaData"):
                metadata = metadata_class(data_table[0]["FileMetaData"], offset_size)
            else:
                return offset, offset_size
        else:
            return offset, offset_size

        from ..Data import convert_to_list
        if not adjust_ids:
            metadata.ids_reserved = 0
            offset = 0
        last_offset_size = metadata.ids_reserved
        current_offset = offset
        for extra_file in metadata.extra_files:
            known_names: set[str] = {o["name"] for o in data_table}
            id_offset = current_offset + last_offset_size

            new_table: list[dict[str, Any]] = convert_to_list(load_data_file(extra_file), "data")
            current_offset, last_size = recursively_find_files_to_load(new_table, id_offset, last_offset_size, adjust_ids=adjust_ids)

            new_names: set[str]= {o["name"] for o in data_table}
            shared_keys = list(new_names & known_names)

            if shared_keys:
                nl = "\n"
                errors.append(f'file {extra_file} contains {len(shared_keys)} key{"s" if len(shared_keys) > 1 else ""} that are shared with existing tables' +
                              f"{nl} Here's the list of those duplicate: [{', '.join(shared_keys)}]")

            else:
                if adjust_ids:
                    for manual_dict in list(new_table):
                        if manual_dict.get("id"):
                            manual_dict["id"] += id_offset
                    new_table[0]["id"] = id_offset

                if current_offset != id_offset: # some file got recursively found
                    last_offset_size = last_size
                elif last_offset_size != metadata.ids_reserved: # restore previous offset
                    last_offset_size = metadata.ids_reserved
                data_table.extend(new_table)

    if errors:
        if len(errors) == 1:
            raise Exception("Found an error in the file data: \n - " + errors[0])
        else:
            raise Exception("Found errors in the files data:" + "\n - ".join(errors))
    return current_offset, last_offset_size
# endregion
# region load_manifest
def load_manifest() -> dict[str, Any]:
    """Use this function to load the data from the archipelago.json file"""
    import json, pkgutil
    try:
        file = pkgutil.get_data(__name__.removesuffix(".hooks.Data"), "archipelago.json")
        if file is not None:
            filedata = json.loads(file.decode())
        else:
            filedata = {}
    except:
        filedata = {}

    return filedata
# endregion
# called after the game.json file has been loaded
def after_load_game_file(game_table: dict) -> dict:
    return game_table

# called after the items.json file has been loaded, before any item loading or processing has occurred
# if you need access to the items after processing to add ids, etc., you should use the hooks in World.py
def after_load_item_file(item_table: list) -> list:
    recursively_find_files_to_load(item_table)
    return item_table


# called after the locations.json file has been loaded, before any location loading or processing has occurred
# if you need access to the locations after processing to add ids, etc., you should use the hooks in World.py
def after_load_location_file(location_table: list[dict[str, Any]]) -> list:
    recursively_find_files_to_load(location_table)
# region create_event
# this part is required for create_event
    global _location_table
    _location_table = location_table
# endregion
    return location_table

# called after the events.json file has been loaded, before any processing has occurred
# If you need access to the events after processing, you should use the hooks in World.py
def after_load_event_file(event_table: list) -> list:
    recursively_find_files_to_load(event_table, adjust_ids=False)
# region create_event
# this region deals with the "create_event" location property
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
        loc_name: str = location["name"]
        event_request = location.get("create_event")
        if not event_request:
            continue

        base_event_override: dict[str, str] = {"copy_location": location["name"]}
        for property, value in location.items():
            if property.lower().startswith("event_"):
                # we have schema for ["event_visible", "event_category"] but others (except "name") should work too
                property_name = property.removeprefix("event_")
                if property_name == "name":
                    logging.warning(f'Warning: Location "{loc_name}" tried to override the created event(s)\'s name using the property "event_name",\
                                    \nit should be set directly in "create_event" instead')
                    continue
                base_event_override[property_name] = value


        if isinstance(event_request, str):
            events_to_make = [event_override(event_request, base_event_override)]
        elif isinstance(event_request, list):
            events_to_make = []
            for i in event_request:
                if isinstance(i, str):
                    events_to_make.append(event_override(i, base_event_override))
                elif isinstance(i, dict):
                    name = i.pop("name")
                    events_to_make.append(event_override(name, base_event_override | i))
                else:
                    raise ValueError("uh what...")
        else:
            events_to_make = [event_override(f"@{loc_name}", base_event_override)]

        for event_obj in events_to_make:
            event: dict[str, str] = {"name": event_obj.name, "enabled_with_location": event_obj.data["copy_location"]} | event_obj.data

            event_table.append(event)
# endregion
    return event_table
# called after the regions.json file has been loaded, before any location loading or processing has occurred
# if you need access to the locations after processing to add ids, etc., you should use the hooks in World.py
def after_load_region_file(region_table: dict) -> dict:
    return region_table

# called after the categories.json file has been loaded
def after_load_category_file(category_table: dict[str, Any]) -> dict:
    return category_table

# called after the categories.json file has been loaded
def after_load_option_file(option_table: dict) -> dict:
    # option_table["core"] is the dictionary of modification of existing options
    # option_table["user"] is the dictionary of custom options
    return option_table

# called after the meta.json file has been loaded and just before the properties of the apworld are defined. You can use this hook to change what is displayed on the webhost
# for more info check https://github.com/ArchipelagoMW/Archipelago/blob/main/docs/world%20api.md#webworld-class
def after_load_meta_file(meta_table: dict) -> dict:
    manifest = load_manifest()
    if not meta_table.get("docs"):
        meta_table['docs'] = {}
    if not meta_table['docs'].get("web"):
        meta_table['docs']['web'] = {}

    meta_table["docs"]["apworld_description"] = f"""
    Manual games allow you to set custom check locations and custom item names that will be rolled into a multiworld.
    the player must manually refrain from using these gathered items until the tracker shows that they have been acquired or sent.
    [Apworld Version: {manifest.get('world_version', 'Unknown')}]
    """
    web = WebWorld() # using a webworld to get attributes type checking
    web.theme = "ocean"
    web.bug_report_page = "https://discord.gg/T5bcsVHByx"
    # web.options_presets = {
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
    meta_table['docs']['web'] |= vars(web)

    return meta_table
