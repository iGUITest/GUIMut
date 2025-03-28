import os


class Screenshot:
    path = ''
    count = 0

    def __init__(self, path, reset):
        Screenshot.path = path
        try:
            if reset:
                Screenshot.count = 0
            # check if the directory exists
                if os.path.exists(Screenshot.path):
                    os.system(f"rm -rf {Screenshot.path}")
            os.makedirs(Screenshot.path, exist_ok=True)
        except Exception as e:
            print(f"Initializing Screenshot directory Error: {e}")
            exit(1)

    @staticmethod
    def take_screenshot(driver, name=None):
        # name is optional, if not provided, use count
        # print(Screenshot.path)
        # print("Taking screenshot at directory:", os.path.abspath(Screenshot.path))
        path = os.path.join(Screenshot.path, f"{name if name else Screenshot.count}.png")
        driver.save_screenshot(path)
        Screenshot.count += 1
        print("Screenshot saved at:", os.path.abspath(path))
        return os.path.abspath(path)