from typing import Any

class HasaimConfiguration():
    def __init__(self, config: dict):
        """
        A dictionary with getter and setter support only.

        Args:
            config: Dictionary to define keys and default values of the config
        """
        self._config = config
    
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

            if self._config.get(key) is None:
                print(f"Config key {key} not found")
                continue
            elif not isinstance(key, str):
                raise TypeError("Config key must be a string")
            elif type(value) != type(self._config[key]):
                raise TypeError("Config type cannot be changed")
            
            self._config[key] = value
        
        return self._config