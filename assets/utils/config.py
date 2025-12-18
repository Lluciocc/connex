import configparser
import os 

CONFIG_PATH = "~/.config/connex/config.ini"

class Configuration:
    def __init__(self, config_path=CONFIG_PATH):
        self.config_path =  os.path.expanduser(config_path)
        self.config = configparser.ConfigParser()


    def load_config(self):
        try:
            self.config.read(self.config_path)
            if not self.config.sections():
                self.create_default_config()
            return True
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return False
        
    def create_default_config(self):
        print("Creating default configuration file.")
        self.config['GENERAL'] = {
            'debug': 'false'
        }
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def get_config(self):
        if self.load_config():
            return self.config
        return None

if __name__ == "__main__":
    config_manager = Configuration()
    config_data = config_manager.get_config()
    if config_data:
        for section in config_data.sections():
            print(f"[{section}]")
            for key, value in config_data.items(section):
                print(f"{key} = {value}")

"""
example config.ini content:
[GENERAL]
debug = true
"""