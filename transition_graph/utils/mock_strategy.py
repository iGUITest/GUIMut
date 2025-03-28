import string
import random


class MockStrategy:

    text_hash_map = {}

    def __init__(self, strategy_name, length=3):
        self.strategy_name = strategy_name
        self.length = length
        if (strategy_name, length) not in self.text_hash_map:
            self.text = self._generate_text()
            self.text_hash_map[(strategy_name, length)] = self.text
        else:
            self.text = self.text_hash_map[(strategy_name, length)]

    def _generate_text(self):
        if self.strategy_name == "random":
            return "".join(random.choices(string.ascii_letters + string.digits, k=self.length))
        elif self.strategy_name == "number":
            return "".join(random.choices(string.digits, k=self.length))
        elif self.strategy_name == "letter":
            return "".join(random.choices(string.ascii_letters, k=self.length))
        elif self.strategy_name == "lowercase":
            return "".join(random.choices(string.ascii_lowercase, k=self.length))
        elif self.strategy_name == "uppercase":
            return "".join(random.choices(string.ascii_uppercase, k=self.length))
        elif self.strategy_name == "alphanumeric":
            return "".join(random.choices(string.ascii_letters + string.digits, k=self.length))
        elif self.strategy_name == "symbol":
            return "".join(random.choices(string.punctuation, k=self.length))
        else:
            raise ValueError("Invalid mock strategy name")

    def generate_text(self):
        return self.text

    @staticmethod
    def is_in_hash_map(text):
        return text in MockStrategy.text_hash_map.values()

    def to_dict(self) -> dict:
        return {
            "strategy_name": self.strategy_name,
            "length": self.length
        }

    @staticmethod
    def hash_map_to_dict():
        current_map = {}
        for key, value in MockStrategy.text_hash_map.items():
            strategy_name, length = key
            # join the key tuple into a string
            key_str = f"{strategy_name}_{length}"
            current_map[key_str] = value
        return current_map

    @staticmethod
    def from_dict(strategy_dict: dict):
        ret = MockStrategy(strategy_dict["strategy_name"], strategy_dict["length"])
        return ret

    @staticmethod
    def hash_map_from_dict(strategy_dict: dict):
        for key, value in strategy_dict.items():
            strategy_name, length = key.split("_")
            MockStrategy.text_hash_map[(strategy_name, int(length))] = value