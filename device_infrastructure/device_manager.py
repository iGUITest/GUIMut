import os
import sys
from time import sleep

import yaml
import subprocess
from appium.options.android import UiAutomator2Options
from appium import webdriver

from device_infrastructure.actions import Screenshot, Package, Activity, Snapshot, Input


class DeviceManager:


    def __init__(self, yaml_file_path, reset=None):
        yaml_file = open(yaml_file_path, "r")
        self.config = yaml.safe_load(yaml_file)
        yaml_file.close()

        # load from config file
        self.desired_caps = {
            "platformName": self.config["appium"]["platformName"],
            "automationName": self.config["appium"]["automationName"],
            "deviceName": self.config["appium"]["deviceName"],
            "appPackage": self.config["appium"]["appPackage"],
            "appActivity": self.config["appium"]["appActivity"],
            "language": self.config["appium"]["language"],
            "locale": self.config["appium"]["locale"],
            "newCommandTimeout": 0,
        }
        self.options = UiAutomator2Options().load_capabilities(self.desired_caps)
        self.driver = webdriver.Remote(self.config["appium"]["serverUrl"], options=self.options)
        # Add noreset
        self.desired_caps.update({"noReset": True})
        self.options = UiAutomator2Options().load_capabilities(self.desired_caps)
        self.screenshot_dir = self.config["screenshotDir"]
        self.package_name = self.config["appium"]["appPackage"]
        self.activity_name = self.config["appium"]["appActivity"]
        self.reset = reset if reset is not None else self.config["reset"]
        self.screenshot = Screenshot(self.screenshot_dir, self.reset)
        self.delay = self.config["delay"]
        self.max_err_count = 5
        self.enabled_coverage_file = self.config["coverageFile"]
        self.coverage_file_dir = self.config["coverageFileDir"]
        self.jacoco_path = self.config["jacocoAgentPath"]

        print("DeviceManager Initialized.")

    def reload_driver(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                old_driver = self.driver
                self.driver = webdriver.Remote(self.config["appium"]["serverUrl"], options=self.options)
                sleep(self.delay)
                old_driver.quit()
                sleep(self.delay)
                break

            except Exception as e:
                if e.msg == "A session is either terminated or not started":
                    print("[WARNING] Session already terminated, ignoring...")
                    break
                print(f"[WARNING] Failed to reload driver: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to reload driver after {self.max_err_count} attempts.")
        return self.driver

    def get_driver(self):
        return self.driver

    def start_package(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                Package.start_package(self.package_name)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to start package: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to start package after {self.max_err_count} attempts.")


    def get_current_activity(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                activity = Activity.get_current_activity()
                break
            except Exception as e:
                print(f"[WARNING] Failed to get current activity: {e}, retrying...")
                sleep(self.delay)
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to get current activity after {self.max_err_count} attempts.")
        return activity

    def start_activity(self, activity):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                Activity.start_activity(activity)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to start activity: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to start activity after {self.max_err_count} attempts.")

    def save_snapshot(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                Snapshot.create_snapshot()
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to save snapshot: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

    def restore_snapshot(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                Snapshot.restore_snapshot()
                sleep(self.delay)
                self.reload_driver()
                break
            except Exception as e:
                print(f"[WARNING] Failed to restore snapshot: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

    def click_by_coordinate(self, x, y):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = Input.click_by_coordinate(self.driver, x, y)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to click by coordinate: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def click_by_xpath(self, xpath):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = Input.click_by_xpath(self.driver, xpath)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to click by xpath: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def back(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = Input.back(self.driver)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to click back: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def hide_keyboard(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = Input.hide_keyboard(self.driver)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to hide keyboard: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def text_input(self, xpath, text):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = Input.text_input(self.driver, xpath, text)
                Input.hide_keyboard(self.driver)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to input text: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def text_clear(self, xpath):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = Input.text_clear(self.driver, xpath)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to clear text: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def take_screenshot(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                status = self.screenshot.take_screenshot(self.driver)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"Failed to take screenshot: {str(e)}")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

        return status

    def get_component_tree(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                component_tree = self.driver.page_source
                break
            except Exception as e:
                print(f"[WARNING] Failed to get component tree: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")
                sleep(self.delay)

        return component_tree

    @staticmethod
    def is_system_activity(activity) -> bool:
        if activity is None:
            return False

        if activity.get("package_name") == "com.google.android.permissioncontroller" and activity.get("activity_name") == "com.android.permissioncontroller.permission.ui.GrantPermissionsActivity":
            return True
            # More system activities can be added here
        else:
            return False


    def get_state(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                state = self.driver.query_app_state(self.package_name)
                activity = self.get_current_activity()
                break
            except Exception as e:
                print(f"[WARNING] Failed to query app state: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")
                sleep(self.delay)

        if DeviceManager.is_system_activity(activity):
            return "running"

        if state == 3:
            return "background"
        elif state == 4:
            return "running"
        else:
            return "halted"


    def to_background(self, time):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                self.driver.background_app(time)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to send app to background: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")


    def terminate(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                self.driver.terminate_app(self.package_name)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to terminate app: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")

    def activate(self):
        from device_infrastructure import DeviceInfraError

        err_count = 0
        while True:
            try:
                self.driver.activate_app(self.package_name)
                break
            except Exception as e:
                print(f"[WARNING] Failed to activate app: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save snapshot after {self.max_err_count} attempts.")
                sleep(self.delay)


    def quit(self):
        from device_infrastructure import DeviceInfraError

        self.save_coverage_file()

        err_count = 0
        while True:
            try:
                self.driver.quit()
                break
            except Exception as e:
                print(f"[WARNING] Failed to quit driver: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"[FATAL] Failed to quit driver after {self.max_err_count} attempts.")
                sleep(self.delay)


    def merge_coverage_files(self, where=None):
        from pathlib import Path
        from device_infrastructure import DeviceInfraError

        if where is not None:
            coverage_file_dir_path = Path(self.coverage_file_dir) / where
            coverage_file_dir_path.mkdir(parents=True, exist_ok=True)
        else:
            coverage_file_dir_path = Path(self.coverage_file_dir)

        err_count = 0
        while True:
            try:
                rm_old_command = f"rm -f {str(coverage_file_dir_path.absolute())}/coverage.ec"
                command = f"java -jar {self.jacoco_path} merge {str(coverage_file_dir_path.absolute())}/*.ec --destfile {str(coverage_file_dir_path.absolute())}/coverage.ec"
                subprocess.run(rm_old_command, shell=True, check=True)
                subprocess.run(command, shell=True, check=True, stdout=sys.stdout, stderr=sys.stderr)
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to save coverage file: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save coverage file after {self.max_err_count} attempts.")
                sleep(self.delay)

    def save_coverage_file(self, where=None):
        import time
        from pathlib import Path
        from device_infrastructure import DeviceInfraError

        if not self.enabled_coverage_file:
            print("[INFO] Coverage file saving is disabled.")
            return

        if where is not None:
            coverage_file_dir_path = Path(self.coverage_file_dir) / where
            coverage_file_dir_path.mkdir(parents=True, exist_ok=True, stdout=sys.stdout, stderr=sys.stderr)
        else:
            coverage_file_dir_path = Path(self.coverage_file_dir)

        err_count = 0
        while True:
            try:
                # Pull the coverage file from the device
                # Using: adb shell run-as ${PACKAGE_NAME} cat files/coverage.ec > ${LOCAL_EC_PATH}
                timestamp = int(time.time())
                command = f"adb shell run-as {self.package_name} cat files/coverage.ec > {str(coverage_file_dir_path.absolute())}/coverage_{timestamp}.ec"
                subprocess.run(command, shell=True, check=True)
                print(f"[INFO] Coverage file saved to {self.coverage_file_dir}/coverage_{timestamp}.ec")
                sleep(self.delay)
                break
            except Exception as e:
                print(f"[WARNING] Failed to save coverage file: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise DeviceInfraError(f"Failed to save coverage file after {self.max_err_count} attempts.")
                sleep(self.delay * 10)


if __name__ == "__main__":
    # Usage example
    device_manager = DeviceManager(yaml_file_path="/Users/xingjunyang/Documents/GitHub/PathMuTeG/config.yaml")
    device_manager.start_package()
    # current_activity = device_manager.get_current_activity()
    # print(f"Current Activity: {current_activity}")
    # device_manager.save_snapshot()
    # device_manager.restore_snapshot()
    # current_activity = device_manager.get_current_activity()
    # print(f"Current Activity: {current_activity}")
    # print(device_manager.take_screenshot())
    # device_manager.click_by_xpath('//android.widget.AutoCompleteTextView[@resource-id="com.github.characterdog.bmicalculator:id/txt_height"]')
    device_manager.text_input('//android.widget.AutoCompleteTextView[@resource-id="com.github.characterdog.bmicalculator:id/txt_height"]', "190")
    device_manager.to_background(2)
    device_manager.quit()