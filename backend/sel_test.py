from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time

options = Options()
#options.add_argument("--headless=new")  # Keep headless option

driver = webdriver.Chrome(options=options)

postcode = "KW17 2ND"
specialty = "Cardiology"
procedure = ""

url = "https://www.phin.org.uk/"
driver.get(url)

wait = WebDriverWait(driver, 5)

# Wait for and click the cookie button
cookie_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button.white.svelte-1j7atkd")))
cookie_button.click()

# Wait for each input field to be visible and interactable
postcode_input = wait.until(EC.visibility_of_element_located((By.NAME, "location-input")))
specialty_input = wait.until(EC.visibility_of_element_located((By.NAME, "specialty-input")))
procedure_input = wait.until(EC.visibility_of_element_located((By.NAME, "procedure-input")))
submission_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".search-button.svelte-1isvcnp")))

# Send keys to each input
postcode_input.send_keys(postcode)
time.sleep(0.25)
specialty_input.send_keys(specialty)
time.sleep(0.25)
procedure_input.send_keys(procedure)

time.sleep(1)

# Wait for and click the submission button
submission_button.click()

time.sleep(1)

doctors_list = driver.find_elements(By.XPATH, "//div[@class='search-result svelte-gx346u']")

# Look through each doctor and get their info, adding their data as an object to a list of doctors' data
doctors = []

if len(doctors_list) == 0:
    try:
        # Increase search radius by clicking the filter buttons
        filter_distance_button = wait.until(EC.element_to_be_clickable((By.ID, "filter-button-distance")))
        filter_distance_button.click()

        accept_distance_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, ".button.blue.svelte-1lakp6")))
        accept_distance_button.click()

        # Allow some time for the new results to load
        time.sleep(1)

        doctors_list = driver.find_elements(By.XPATH, "//div[@class='search-result svelte-gx346u']")
        
        if len(doctors_list) == 0:
            print("No doctors found after increasing search radius.")
            # Handle the case where no doctors are found after increasing radius.
    except Exception as e:
        print(f"Error while filtering distance: {e}")

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
        print(f"Error processing doctor: {e}")

print(doctors)
