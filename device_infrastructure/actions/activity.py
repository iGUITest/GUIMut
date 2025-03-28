import subprocess


class Activity:
    @staticmethod
    def __parse_activity__(activity):
        """解析Activity信息"""
        """信息的类型：mCurrentFocus=Window{<?component_hash> <?u0> <package_name>/<activity_name>}"""
        """前两个参数可有可无，但是如果有的话，需要通过正则表达式提取出来"""
        """从后面往前匹配"""
        import re
        pattern = r'mCurrentFocus=Window\{(?:([\w\d]+)\s+)?(?:([\w\d]+)\s+)?([\w\d\-.]+)/([\w\d\-.]+)\}'

        match = re.search(pattern, activity)

        if match:
            # 解析匹配到的字段
            first = match.group(1)
            second = match.group(2)
            package_name = match.group(3)
            activity_name = match.group(4)

            # 处理赋值逻辑
            if second:
                component_hash = first
                u0 = second
            else:  # 如果 `second` 为空，则 `first` 其实是 `u0`
                component_hash = None
                u0 = first

            return {
                "component_hash": component_hash,
                "u0": u0,
                "package_name": package_name,
                "activity_name": activity_name
            }
        else:
            return None


    @staticmethod
    def get_current_activity():
        cmd = f"adb shell dumpsys window | grep -E 'mCurrentFocus'"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=5  # Add timeout to prevent hanging
        )

        if result.returncode == 0 or result.returncode == 1:
            activity = Activity.__parse_activity__(result.stdout)
            print(f"Current Activity: {activity}")
            return activity
        else:
            print(f"ADB Shell Error: {result.stderr}")
            return None

    @staticmethod
    def start_activity(activity):
        cmd = f"adb shell am start -n {activity['package_name']}/{activity['activity_name']}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"Activity {activity.activity_name} started successfully")
        else:
            print("Start activity Error")
            print(result.stderr)
            exit(1)


if __name__ == "__main__":
    # Test the Activity class
    print(Activity.__parse_activity__("mCurrentFocus=Window{u0 com.example.app/com.example.app.MainActivity}"))
    print(Activity.start_activity(Activity.__parse_activity__("mCurrentFocus=Window{u0 com.example.app/com.example.app.MainActivity}")))