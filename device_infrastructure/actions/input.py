from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class Input:

    @staticmethod
    def click_by_coordinate(driver, x, y):
        try:
            driver.tap([(x, y)], 100)
        except Exception as e:
            print(f"Click by Coordinate Error: {e}")
            return False

        return True

    @staticmethod
    def click_by_xpath(driver, xpath):
        try:
            element = driver.find_element(by=AppiumBy.XPATH, value=xpath)
            element.click()
        except Exception as e:
            print(f"Click by Xpath Error: {e}")
            return False

        return True

    @staticmethod
    def back(driver):
        try:
            driver.back()
        except Exception as e:
            print(f"Back Error: {e}")
            return False

        return True

    @staticmethod
    def hide_keyboard(driver):
        if driver.is_keyboard_shown():
            driver.hide_keyboard()

        if driver.is_keyboard_shown():
            print(f"Keyboard is still shown Error")

    @staticmethod
    def text_input(driver, xpath, text):
        try:
            element = driver.find_element(by=AppiumBy.XPATH, value=xpath)
            input_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((AppiumBy.XPATH, xpath))
            )
            input_element.send_keys(text)
            if element.text != text:
                print(f"Input text not as expected Error: {text} != {element.text}")
                return False

            if Input.hide_keyboard(driver) is False:
                return False

        except Exception as e:
            print(f"Input text Error: {e}")
            return False

        return True

    @staticmethod
    def text_clear(driver, xpath):
        try:
            element = driver.find_element(by=AppiumBy.XPATH, value=xpath)
            element.clear()
        except Exception as e:
            print(f"Text clear Error: {e}")
            return False

        return True