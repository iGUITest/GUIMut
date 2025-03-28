import subprocess


class Snapshot:
    @staticmethod
    def create_snapshot():
        cmd = "adb emu avd snapshot save snapshot"
        result = subprocess.run(cmd, shell=True, check=True)
        if result.returncode == 0:
            print("Successfully saved snapshot")
        else:
            print("Save snapshot Error")
            exit(1)

    @staticmethod
    def restore_snapshot():
        cmd = "adb emu avd snapshot load snapshot"
        result = subprocess.run(cmd, shell=True, check=True)
        if result.returncode == 0:
            print("Successfully restored snapshot")
        else:
            print("Restore snapshot Error")
            exit(1)