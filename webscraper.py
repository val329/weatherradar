from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import csv
import time
import os

# Start the timer
start_time = time.perf_counter()

## ---------------------------------------------------------------##
# helper functions


def export_to_csv(filename, headers, results_list):
    """write data to CSV / save data / export"""

    if not results_list:                                    # results list empty
        print("Export not completed: no data to write")

    if len(headers) != len(results_list[0]):                # headers don't match results list
        print("Export not completed: incorrect headers data")
        return
    
    file_exists = os.path.exists(filename + ".csv")         # check if the file already exists before opening it

    with open(filename + ".csv", "a", newline="") as file:  # append rows if a file exists, create a new file if not
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(headers)
        
        for row in results_list:
            line = []
            for key in row:
                line.append(row[key])
            writer.writerow(line)
        print("Export completed")


def find_element_ext(self, by, value):
    """extension of webdriver find_element, added handling exceptions"""
    try:
        return self.find_element(by, value)
    except Exception:
        print(f'Element "{value}" not found')
        raise Exception


def find_elements_ext(self, by, value):
    """extension of webdriver find_elements, added handling exceptions"""
    try:
        return self.find_elements(by, value)
    except Exception:
        print(f'Element "{value}" not found')
        return []


def parse_row_section(tds, index, utc_time):
    """parse table row sections into dictionary. total 8 td entries, 2 sections"""
    city = tds[index].find_element(By.TAG_NAME, "a").text
    localtime = tds[index + 1].text
    desc = tds[index + 2].find_element(By.TAG_NAME, "img").get_attribute("alt")
    temp = tds[index + 3].text

    return {
        "city": city,
        "localtime": localtime,
        "desc": desc,
        "temp": temp,
        "utc_time": utc_time,
    }


## ---------------------------------------------------------------##


# attach extended functions to WebDriver and WebElement
WebDriver.find_element_ext = find_element_ext
WebElement.find_element_ext = find_element_ext
WebDriver.find_elements_ext = find_elements_ext
WebElement.find_elements_ext = find_elements_ext


service = Service()
driver = webdriver.Chrome(service=service)
driver.get("https://www.timeanddate.com/weather/?low=5&sort=0")


# extracting UTC date and time from page footer
footer = driver.find_element_ext(By.CSS_SELECTOR, 'div[id="tb-foot"]')
links_footer = footer.find_elements_ext(By.TAG_NAME, "p")
current_datetime = []
if len(links_footer) > 0:
    for link in links_footer:
        current_datetime.append(link.text)

# extracting time and weather data from 'Local Time and Weather Around the World' page
table = driver.find_element_ext(By.CSS_SELECTOR, "table.zebra.fw.tb-theme")  # table with data <table>
table_body = table.find_element_ext(By.CSS_SELECTOR, "tbody")  # table body excluding headers <tbody>
table_rows = table_body.find_elements_ext(By.CSS_SELECTOR, "tr")  # rows inside the table, each contains 2 cities with data <tr>

results = []
if table_rows:
    for line in table_rows:
        row_left, row_right = {}, {}
        tds = line.find_elements_ext(By.TAG_NAME, "td")
        if len([el for el in tds if el.text.strip()]) > 4:  # if only left half of the row exists
            row_right = parse_row_section(tds, 4, current_datetime[2])
        row_left = parse_row_section(tds, 0, current_datetime[2])

        results.append(row_left)
        results.append(row_right)


export_to_csv(
    "scraped_data",
    ["City", "Local time", "Description", "Temperature", "UTC time"],
    results,
)


driver.quit()


## ---------------------------------------------------------------##
# Stop the timer
end_time = time.perf_counter()
elapsed_time = end_time - start_time

print(f"Execution time: {elapsed_time:.4f} seconds")
