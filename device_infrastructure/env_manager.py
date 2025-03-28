import os
import shlex
import signal
import subprocess
from time import sleep

import yaml


class EnvManager:


    def __init__(self, yaml_file_path):
        yaml_file = open(yaml_file_path, "r")
        self.config = yaml.safe_load(yaml_file)
        yaml_file.close()

        self.delay = self.config["delay"]
        self.max_err_count = 5
        self.emulator_process = None
        self.appium_process = None
        self.script_dir = self.config["scriptDir"]
        self.app_package_name = self.config["appium"]["appPackage"]
        self.emulator = self.config["env"]["emulator"]
        self.emulator_path = self.config["env"]["emulatorPath"]

        # Check if the emulator is already running and kill it
        try:
            self.kill_qemu()  # Kill existing QEMU processes
        except Exception as e:
            print(f"[WARNING] Failed to kill existing QEMU processes: {e}")

        # Check if Appium is already running and kill it
        try:
            self.kill_port(4723)  # Port 4723 is the default port for Appium
        except Exception as e:
            print(f"[WARNING] Failed to kill existing Appium processes: {e}")

        self.__init_avd()  # Initialize the Android Virtual Device (AVD)
        self.__init_appium()  # Initialize the Appium server

    def __init_avd(self):
        # Initialize the AVD
        err_count = 0
        while True:
            try:
                unlock_cmd = f"rm -rf ~/.android/avd/{self.emulator}.avd/*.lock"
                subprocess.run(unlock_cmd, shell=True)

                emulator_path = self.emulator_path
                avd_name = self.emulator
                start_cmd = f"{emulator_path} -avd {avd_name} -no-snapshot-load"
                self.emulator_process = subprocess.Popen(start_cmd, shell=True)  # Start the emulator in a separate process
                sleep(30)  # Wait for the emulator to start
                print("Emulator started successfully.")
                break
            except Exception as e:
                print(f"[WARNING] Failed to start emulator: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise Exception(f"[FATAL] Failed to start emulator after {self.max_err_count} attempts.")
                sleep(self.delay)

    def __init_appium(self):
        # Initialize the Appium Server
        err_count = 0
        while True:
            try:
                appium_cmd = "appium --session-override --log-level error"
                self.appium_process = subprocess.Popen(appium_cmd, shell=True)  # Start Appium server in a separate process
                sleep(self.delay * 5)  # Wait for the Appium server to start
                print("Appium server started successfully.")
                break
            except Exception as e:
                print(f"[WARNING] Failed to start Appium server: {e}, retrying...")
                err_count += 1
                if err_count > self.max_err_count:
                    raise Exception(f"[FATAL] Failed to start Appium server after {self.max_err_count} attempts.")
                sleep(self.delay)

    def install_apk(self, script_dir):
        apk_name = "app-debug.apk"
        cmd = f"adb install {script_dir}/{apk_name}"
        result = subprocess.run(cmd, shell=True, check=False)
        if result.returncode == 0:
            print(f"Successfully Installed apk [Script Directory: {script_dir}]")
        else:
            print(f"Install apk Error [Script Directory: {script_dir}]")
        sleep(self.delay * 5)

    def uninstall_apk(self, app_package_name):
        cmd = f"adb uninstall {app_package_name}"
        result = subprocess.run(cmd, shell=True, check=False)
        if result.returncode == 0:
            print(f"Successfully Uninstalled apk [Package Name: {app_package_name}")
        else:
            print(f"Uninstall apk Error [Package Name: {app_package_name}")
        sleep(self.delay * 5)


    def quit(self):
        # Quit the emulator and Appium server
        if self.emulator_process:
            self.emulator_process.terminate()
            self.emulator_process.wait()
            print("Emulator terminated.")

        if self.appium_process:
            self.appium_process.terminate()
            self.appium_process.wait()
            print("Appium server terminated.")

    def restart(self):
        # Restart the emulator and Appium server
        print("Restarting emulator and Appium server...")
        self.quit()
        self.__init_avd()
        self.__init_appium()
        print("Restart completed successfully.")

    def kill_qemu(self):
        err_count = 0

        while True:
            try:
                pgrep_cmd = "pgrep -l qemu-system-aarch64"
                result = subprocess.run(shlex.split(pgrep_cmd), capture_output=True, text=True)

                if result.returncode == 0 and result.stdout:
                    print(f"Found QEMU Process:\n{result.stdout}")
                    pids = [line.split()[0] for line in result.stdout.splitlines()]

                    # Kill each QEMU process
                    for pid in pids:
                        kill_cmd = f"kill -9 {pid}"
                        subprocess.run(shlex.split(kill_cmd), check=True)
                        print(f"Killed PID: {pid}")
                else:
                    print("No QEMU processes found.")
                break
            except subprocess.CalledProcessError as e:
                print(f"Failed to execute command: {e}")
                break
            except Exception as e:
                print(f"Error occurred while killing QEMU processes: {e}")
                err_count += 1
                if err_count > self.max_err_count:
                    raise Exception(f"Failed to kill QEMU processes after {self.max_err_count} attempts.")

    def kill_port(self, port):
        err_count = 0
        while True:
            try:
                # Execute lsof command
                output = subprocess.check_output(["lsof", "-i", f":{port}"], stderr=subprocess.PIPE, text=True)
                lines = output.splitlines()

                if not len(lines) > 1:  # First line is header
                    print(f"No processes found using port {port}")
                    break

                # Parse and kill each process
                for line in lines[1:]:  # Skip header
                    parts = line.split()
                    pid = parts[1]  # Second column is PID
                    print(f"Killing process {pid}...")
                    try:
                        os.kill(int(pid), signal.SIGKILL)  # Equivalent to kill -9
                    except Exception as e:
                        print(f"Failed to kill process {pid}: {e}")

                print("Port freed successfully")
                break

            except subprocess.CalledProcessError:
                print(f"No processes found using port {port}")
                break
            except Exception as e:
                print(f"Error occurred: {e}")
                err_count += 1
                if err_count > 5:
                    raise Exception(f"Failed to kill processes on port {port} after multiple attempts.")
                sleep(self.delay)