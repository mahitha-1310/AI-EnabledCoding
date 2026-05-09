import streamlit as st
from typing import Any

_MAPPINGS = {
    bool: st.checkbox,
    float: st.number_input,
    str: st.text_input,
    list: st.selectbox,
    "multiselect": st.multiselect
}

def iter_list(item_list: list[Any], index: int = 0) -> dict[str, Any]:
    if index >= len(item_list) or index < 0:
        raise ValueError("Index must be within bounds of item_list size")

    return {
        "options": item_list,
        "index": index
    }

def iter_multilist(item_list: list[Any], defaults: list[Any]) -> dict[str, Any]:
    if not all(d in item_list for d in defaults):
        raise ValueError("All defaults must be present in item_list")

    return {
        "options": item_list,
        "default": defaults
    }

class HasaimConfiguration():

    def __init__(self, config: dict):
        """
        A dictionary with getter and setter support only.

        Args:
            config: Dictionary to define keys and default values of the config
        """
        self._config = config
    
    def __getitem__(self, key: str) -> Any:
        return self._config[key]

    def get(self, key: str) -> Any:
        """
        Get a config value using a key.

        Args:
            key: A string refering to a specific config value
        Returns:
            value associated with the key
        """
        return self._config.get(key)

    def set(self, config: dict) -> None:
        """
        Set defined config values within the config. 
        It cannot add new config values or change the type of config values.

        If the config key is not found in the config, the config value will not be added or applied.

        Args:
            key: A dictionary with keys that already exist in the dictionary
        """

        for key, value in config.items():

            if key not in self._config:
                print(f"Config key {key} not found")
                continue
            elif not isinstance(key, str):
                raise TypeError("Config key must be a string")

            expected_type = type(self._config[key])
            if not isinstance(value, expected_type):
                try:
                    value = expected_type(value)
                except (ValueError, TypeError):
                    raise TypeError(f"Config value for '{key}' must be of type {expected_type.__name__}")

            self._config[key] = value
    
    def list_item(self, config_name: str) -> Any:
        return self._config[config_name]["options"][self._config[config_name]["index"]]

    def list_items(self, config_name: str) -> list[Any]:
        """Return the current selection from a multiselect config value."""
        return self._config[config_name]["default"]

    def display(self, key: str, text: str | None = None, override_type: Any = None, **kwargs) -> Any:
        if key not in self._config:
            raise KeyError(f"Config value {key} not found in config")

        value = self._config[key]
        label = key.replace("_", " ").title()

        if isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
            kwargs["format"] = "%0f"
 
        if override_type == "multiselect" or (isinstance(value, dict) and "default" in value):
            if "options" not in kwargs:
                kwargs["options"] = value["options"]
                kwargs["default"] = value["default"]
        elif override_type is list or isinstance(value, dict):
            if "options" not in kwargs:
                kwargs["options"] = value["options"]
                kwargs["index"]   = value["index"]
        else:
            kwargs["value"] = value

        result = self._get_mapping(key=key, label=label, override_type=override_type, **kwargs)
        if text:
            self._add_description(text)

        # Write the widget's current value back into the config so accessors reflect the UI state
        if override_type == "multiselect" or (isinstance(self._config[key], dict) and "default" in self._config[key]):
            self._config[key]["default"] = result
        elif override_type is list or (isinstance(self._config[key], dict) and "index" in self._config[key]):
            options = self._config[key]["options"]
            self._config[key]["index"] = options.index(result) if result in options else self._config[key]["index"]
        else:
            # Preserve the original type (e.g. int config values rendered as float by st.number_input)
            orig_type = type(self._config[key])
            try:
                self._config[key] = orig_type(result)
            except (TypeError, ValueError):
                self._config[key] = result

        return result

    def _get_mapping(self, key: str, label: str, override_type: Any = None, **kwargs) -> Any:

        value = kwargs["value"] if "value" in kwargs else kwargs.get("options")

        if override_type:
            return _MAPPINGS[override_type](label=label, key=key, **kwargs)
        else:
            for value_type, function in _MAPPINGS.items():
                if isinstance(value, value_type):
                    return function(label=label, key=key, **kwargs)

        raise TypeError(f"Type of value '{value}' ({type(value).__name__}) not supported")
    
    def _add_description(self, txt: str, md=True, width="stretch") -> None:
        if md:
            st.markdown(txt, width=width)
        else:
            st.text(txt, width=width)