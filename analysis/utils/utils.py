def get_scenario_name_from_file(file_name: str):
    if file_name.startswith("scenario_") and file_name.endswith(".txt"):
        return file_name[len("scenario_") : -len(".txt")]
    return None


def get_data_source_from_file(file_name: str, file_path: str):
    folder_name = file_path.split("/")[-1]
    # attach category folder name to path
    # agent is only aware of path upto processed
    # file name and category in which it is in is dynamic
    return f"{folder_name}/{file_name}" if folder_name else file_name
