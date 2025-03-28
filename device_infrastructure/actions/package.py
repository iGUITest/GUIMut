import subprocess


class Package:
    @staticmethod
    def start_package(package_name):
        command = f"adb shell monkey -p {package_name} -c android.intent.category.LAUNCHER 1"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Start package Error: {result.stderr}")
            exit(1)
        print(result.stdout.strip())