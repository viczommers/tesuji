from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from pydantic import BaseModel, Field
from portia.tool import Tool, ToolRunContext
import time
import json


#Define schema
class PhinToolSchema(BaseModel):

    postcode: str = Field(..., 
                          description="",)

    insurance_company: str = Field(..., 
                          description="",)

    specialty: str = Field(..., 
                          description="",)

    procedure: str = Field(..., 
                          description="",)


class PhinTool(Tool[list]):

    args_schema: type[BaseModel] = PhinToolSchema

    description: str = ""

    output_schema: tuple[str, list[str]] = ("", "")

    def run(self, _: ToolRunContext, 
            postcode: str, insurance_company: str, specialty: str, procedure: str) -> str | list[str]:

        driver = webdriver.Chrome()

        url = "https://www.phin.org.uk/"

        driver.get(url)

        wait = WebDriverWait(driver, 5)
        cookie_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button.white.svelte-1j7atkd")))
        cookie_button.click()
        postcode_input = driver.find_element(By.NAME, "location-input")
        specialty_input = driver.find_element(By.NAME, "specialty-input")
        procedure_input = driver.find_element(By.NAME, "procedure-input")
        time.sleep(0.5)
        postcode_input.send_keys(postcode)
        time.sleep(0.5)
        specialty_input.send_keys(specialty)
        time.sleep(0.5)
        procedure_input.send_keys(procedure)

        submission_button = driver.find_element(By.CSS_SELECTOR, ".search-button.svelte-1isvcnp")
        submission_button.click()
        time.sleep(20)

