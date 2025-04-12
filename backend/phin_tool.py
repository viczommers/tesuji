from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from pydantic import BaseModel, Field
from portia.tool import Tool, ToolRunContext
import time
import json
from selenium.webdriver.chrome.options import Options 

#Define schema
class PhinToolSchema(BaseModel):

    postcode: str = Field(..., 
                          description="",)

    insurance_company: str = Field(default="", description="This field is optional")

    specialty: str = Field(default="", description="This field is optional")

    procedure: str = Field(default="", description="This field is optional")


class PhinTool(Tool[list]):

    id: str = "phin_tool"
    name: str = "PHIN Tool"
    description: str = "Fetches data from the PHIN UK site"

    args_schema: type[BaseModel] = PhinToolSchema

    output_schema: tuple[str, list[str]] = ("", "")

    def run(self, _: ToolRunContext, 
            postcode: str, insurance_company: str = "", specialty: str = "", procedure: str = "") -> str | list[str]:

        chrome_options = Options()
        chrome_options.add_argument("--headless")

        driver = webdriver.Chrome(options=chrome_options)

        url = "https://www.phin.org.uk/"

        driver.get(url)

        wait = WebDriverWait(driver, 10)  # Increased timeout to 10 seconds

        # Wait for and click the cookie button
        cookie_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button.white.svelte-1j7atkd")))
        cookie_button.click()
        
        # Wait for input elements to be visible
        postcode_input = wait.until(EC.visibility_of_element_located((By.NAME, "location-input")))
        specialty_input = wait.until(EC.visibility_of_element_located((By.NAME, "specialty-input")))
        procedure_input = wait.until(EC.visibility_of_element_located((By.NAME, "procedure-input")))

        postcode_input.send_keys(postcode)
        postcode_input.send_keys(Keys.TAB)
        postcode_input.send_keys(Keys.ENTER)
        specialty_input.send_keys(specialty)
        procedure_input.send_keys(procedure)

        wait.until(lambda driver: postcode_input.get_attribute('value') == postcode)
        wait.until(lambda driver: specialty_input.get_attribute('value') == specialty)
        wait.until(lambda driver: procedure_input.get_attribute('value') == procedure)

        # Wait for submission button to be clickable
        search_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".search-button.svelte-1isvcnp")))
        search_button.click()

        # Wait for search results to be present
        doctors_list = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".search-result.svelte-gx346u")))

        # Look through each doctor and get their info, adding their data as an object to a list of doctors' data
        doctors = []

        for doctor in doctors_list[:10]:
            try:
                doctor_name = doctor.find_element(By.CSS_SELECTOR, ".name.svelte-1n2ywad").text
                doctor_specialty = doctor.find_element(By.CSS_SELECTOR, ".value.svelte-ivi3vh").text
                doctor_rating = doctor.find_element(By.CSS_SELECTOR, ".value.svelte-vnlxoq").text
                doctor_distance = doctor.find_element(By.XPATH, "(//td[@data-description='Distance'])").text
                doctor_price = doctor.find_element(By.XPATH, "(.//div[@data-description='Fee']//div)").text
                doctor_data = {
                    'name': doctor_name,
                    'specialty': doctor_specialty,
                    'rating': doctor_rating,
                    'distance': doctor_distance,
                    'price': doctor_price
                }
                doctors.append(doctor_data)
            except Exception as e:
                print(f"Error extracting data for a doctor: {e}")
                pass

        driver.quit()
        return doctors