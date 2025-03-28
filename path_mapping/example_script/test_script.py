# This sample code supports Appium Python client >=2.3.0
# pip install Appium-Python-Client
# Then you can paste this into a file and simply run with Python

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

# For W3C actions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

options = AppiumOptions()
options.load_capabilities({
	"platformName": "Android",
	"appium:automationName": "uiautomator2",
	"appium:deviceName": "android",
	"appium:appPackage": "com.example.myapplication",
	"appium:appActivity": "com.example.myapplication.MainActivity",
	"appium:language": "en",
	"appium:locale": "US",
	"appium:serverUrl": "http://localhost:4723",
	"appium:ensureWebviewsHavePages": True,
	"appium:nativeWebScreenshot": True,
	"appium:newCommandTimeout": 3600,
	"appium:connectHardwareKeyboard": True
})

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

el1 = driver.find_element(by=AppiumBy.XPATH, value='//android.widget.EditText[@resource-id="com.example.myapplication:id/editTextNumber"]')
el1.send_keys("123")
el2 = driver.find_element(by=AppiumBy.XPATH, value='//android.widget.EditText[@resource-id="com.example.myapplication:id/editTextNumber2"]')
el2.send_keys("456")
el3 = driver.find_element(by=AppiumBy.XPATH, value='//android.widget.Button[@resource-id="com.example.myapplication:id/button"]')
el3.click()

