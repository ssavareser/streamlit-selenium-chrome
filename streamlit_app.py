import streamlit as st
import os
import time
from bs4 import BeautifulSoup
import pandas as pd
import xlwt
from xlwt.Workbook import *
from pandas import ExcelWriter
import xlsxwriter
from PIL import Image
import io
import base64
import zipfile

# Configure the page title, favicon, layout, etc
st.set_page_config(page_title="Radia IPaC",
                   page_icon="radia-logo-large.png",
                   layout="wide")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def add_background_image(image_file):
    bin_str = get_base64_of_bin_file(image_file)
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{bin_str}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def introPage():
    file = st.file_uploader(label="Upload a zip file")
    with st.spinner('Wait for it...'):
        if file is not None:
            if file.type == "application/zip" or file.name.endswith('.zip'):
              st.write(f"Uploaded file: {file.name}")
              st.write(f"File type: {file.type}")
              # Ensure the temp_files directory exists
              os.makedirs("temp_files", exist_ok=True)
              # Save the uploaded file to a temporary location
              temp_file_path = os.path.abspath(os.path.join("temp_files", file.name))
              with open(temp_file_path, "wb") as f:
                  f.write(file.getbuffer())
              
              # Extract the zip file and check for required files
              required_extensions = {".shp", ".shx", ".dbf"}
              optional_extension = ".prj"
              found_files = set()
              with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                  zip_ref.extractall("temp_files")
                  for file_name in zip_ref.namelist():
                      _, ext = os.path.splitext(file_name)
                      if ext.lower() in required_extensions:
                          found_files.add(ext.lower())
                      elif ext.lower() == optional_extension:
                          found_files.add(ext.lower())
  
              # Check if all required files are present
              if required_extensions.issubset(found_files):
                  st.success("All required shapefile components are present.")
                  return temp_file_path
              else:
                  st.error("The zip file is missing one or more required shapefile components (*.shp, *.shx, *.dbf).")
                  return None
            else:
                st.error("Please upload a valid zip file.")
                return None
    return None


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    service = Service(
        ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
    )

    return webdriver.Chrome(service=service, options=options)


    
    

def run_selenium(shapefile_path):
    driver = get_driver()
    driver.get("https://ipac.ecosphere.fws.gov/location/index")   
    try:
       

        # Wait for the "Upload shape file" button to be present
        upload_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-action-name="show-upload-shape-modal"]'))
        )
        print("Upload button found")

        # Scroll the button into view using JavaScript
        driver.execute_script("arguments[0].scrollIntoView(true);", upload_button)
        print("Upload button scrolled into view")

        # Retry clicking the button using JavaScript
        retries = 3
        for attempt in range(retries):
            try:
                driver.execute_script("arguments[0].click();", upload_button)
                print("Upload button clicked")
                break
            except Exception as e:
                print(f"Retry {attempt + 1}/{retries} to click upload button failed: {e}")
                time.sleep(2)
        else:
            print("Failed to click the upload button after several attempts")
            return
        
        driver.maximize_window()
        driver.execute_script("document.body.style.zoom='100%'")
        
        # Wait for the modal to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'shape-file-input'))
        )
        print("Upload modal opened")

        


        # Retry finding the file input
        file_input_retries = 3
        for attempt in range(file_input_retries):
            try:
                file_input = driver.execute_script("""
                var elem = document.getElementById('shape-file-input');
                elem.style.display = 'block';
                elem.style.visibility = 'visible';
                elem.style.opacity = 1;
                return elem;
                """)

                print("File input found and clickable")
                break
            except Exception as e:
                print(f"Retry {attempt + 1}/{file_input_retries} to find file input failed: {e}")
                logs = driver.get_log('browser')
                time.sleep(2)
        else:
            print("Failed to find or click the file input after several attempts")
            return

        # Ensure the shapefile path exists
        if os.path.exists(shapefile_path):
            print("Shapefile path exists")
            # Send the file path to the file input
            file_input.send_keys(shapefile_path)
            print("File path sent to input")
        else:
            print(f"Shapefile path does not exist: {shapefile_path}")
            return

        print('Shapefile uploaded successfully!')

         # Wait for and click the OK button
        ok_button = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '/html/body/div[2]/div[2]/div/div/div[3]/button'))
        )
        driver.execute_script("arguments[0].click();",ok_button)
        print("OK button clicked")
        

        # Wait for and click the continue button using JavaScript
        try:
            continue_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '/html/body/div[2]/main/div[2]/ul/li[3]/div[3]/form/button'))
            )
            print("Continue button found and clickable")
        except TimeoutException:
            print("Timeout: Continue button not found or clickable within 10 seconds")
            # Optionally handle timeout case here

        # Click using JavaScript if found
        if continue_button:
            try:
                driver.execute_script("arguments[0].click();", continue_button)
                print("Continue button clicked")
            except Exception as e:
                print(f"Error clicking Continue button: {e}")
        else:
            print("Continue button not found or clickable")

        types = []
        entrytypes = []
        commonnames = []
        scientificnames =[]
        ranges = []
        statuses = []

        bcommonnames = []
        bscientificnames = []
        bconcerns = []
        bbreedingseasons = []

        ecommonnames = []
        escientificnames = []
        econcerns = []
        ebreedingseasons = []

        # Use sets to track unique entries
        bird_unique_entries = set()

        # Wait for the animal list to be present
        toggle_button = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="endangered-species-tab"]/div[2]'))  # Adjust as necessary
        )
    
        print("thumbnail/list toggle found")

        if toggle_button:
            try:
                list_button = WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="endangered-species-tab"]/div[2]/button[2]'))  # Adjust as necessary
                )
                driver.execute_script("arguments[0].click();", list_button)
                print("list button clicked")
            except Exception as e:
                print(f"Error clicking list button: {e}")
        else:
            print("list button not found or clickable")

        animal_data = WebDriverWait(driver, 20).until(
            EC.visibility_of_element_located(((By.XPATH, '//*[@id="main-body"]/div[1]/div/aside/div/div[1]/ul')))
        )
        print("resources found")

                # Locate the material tab content
        material_tab_content = driver.find_element(By.CSS_SELECTOR, "div.material.tab-content")

        # 
        #<li class="population even" data-class-name="ProjectPopulation" data-id="10043" data-toggle="modal" data-target="#details-es-10043" tabindex="0">
        # endangered species tab
        animals = driver.find_elements(By.CSS_SELECTOR, "li.population[data-class-name='ProjectPopulation'][data-toggle='modal'][data-target^='#details-es-']")
        for animal in animals:
            try:
                animal_cat_element = animal.find_element(By.XPATH, "preceding::li[@class='non-data header group-header'][1]/h3")
                animal_cat_name = animal_cat_element.text.strip() if animal_cat_element else "Unknown"
            except Exception as e:
                animal_cat_name = "N/A"

            try:
                common_name_element = animal.find_element(By.CSS_SELECTOR, "span.short-name")
                common_name = common_name_element.text.strip() if common_name_element else "N/A"
            except Exception as e:
                common_name = "N/A"

            try:
                scientific_name_element = animal.find_element(By.CSS_SELECTOR, "span.scientific-name")
                scientific_name = scientific_name_element.text.strip() if scientific_name_element else "N/A"
            except Exception as e:
                scientific_name = "N/A"

            try:
                status_element = animal.find_element(By.CSS_SELECTOR, "div.col-sm-4 > span")
                status = status_element.text.strip() if status_element else "N/A"
            except Exception as e:
                status = "N/A"

            try:
                category_element = animal.find_element(By.CSS_SELECTOR, "div.population-name.small")
                category = category_element.text.strip() if category_element else "N/A"
            except Exception as e:
                print("Error finding category:", e)
                category = "N/A"

            types.append(animal_cat_name)
            commonnames.append(common_name)
            scientificnames.append(scientific_name)
            ranges.append(category)
            statuses.append(status)

            print(f"Animal type: {animal_cat_name}")
            print(f"Common Name: {common_name}")
            print(f"Scientific Name: {scientific_name}")
            print(f"Status: {status}")
            print(f"Category: {category}")

        
        birds = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.migratory-bird[data-class-name='ProjectMigbird'][data-toggle='modal'][data-target^='#details-mb-']"))
        )

        for bird in birds:
            try:
                bcommon_name_element = bird.find_element(By.CSS_SELECTOR, "span.short-name")
                bcommon_name = bcommon_name_element.get_attribute("innerText").strip()
                
            except Exception as e:
                bcommon_name = "N/A"

            try:
                bscientific_name_element = bird.find_element(By.CSS_SELECTOR, "span.scientific-name")
                bscientific_name = bscientific_name_element.get_attribute("innerText").strip()
                
            except Exception as e:
                bscientific_name = "N/A"

            try:
                concern_element = bird.find_element(By.CSS_SELECTOR, "div.small.hidden-print")
                concern = concern_element.get_attribute("innerText").strip()
                
            except Exception as e:
                concern = "N/A"

            try:
                breedingseason_element = bird.find_element(By.CSS_SELECTOR, "p.breeding-season")
                breedingseason = breedingseason_element.get_attribute("innerText").strip()
                breedingseason = ' '.join(breedingseason.split())
                
            except Exception as e:
                breedingseason = "N/A"

            try:
                data_target = bird.get_attribute("data-target")
                if "-eagles" in data_target:
                    ecommonnames.append(bcommon_name)
                    escientificnames.append(bscientific_name)
                    econcerns.append(concern)
                    ebreedingseasons.append(breedingseason)
            except Exception as e:
                print("Error checking if bird is an eagle:", e)

            # Create a unique key for the bird entry
            bird_key = (bcommon_name, bscientific_name, concern, breedingseason)

            if bird_key not in bird_unique_entries:
                bird_unique_entries.add(bird_key)
                
                print(f"Common Name: {bcommon_name}")
                print(f"Scientific Name: {bscientific_name}")
                print(f"Level of Concern: {concern}")
                print(f"Breeding Season: {breedingseason}")

                bcommonnames.append(bcommon_name)
                bscientificnames.append(bscientific_name)
                bconcerns.append(concern)
                bbreedingseasons.append(breedingseason)

        # facilities = WebDriverWait(driver, 10).until(
        #     EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li.migratory-bird[data-class-name='ProjectMigbird'][data-toggle='modal'][data-target^='#details-mb-']"))
        # )

        # Create a DataFrame
        edspeciesdf = pd.DataFrame({
            'Type': types,
            'Common Name': commonnames,
            'Scientific Name': scientificnames,
            'Range': ranges,
            'Status': statuses,
        })

        eaglesdf = pd.DataFrame({
            'Common Name': ecommonnames,
            'Scientific Name': escientificnames,
            'Level of Concern': econcerns,
            'Breeding Season': ebreedingseasons,

        })

        migratorydf = pd.DataFrame({
            'Common Name': bcommonnames,
            'Scientific Name': bscientificnames,
            'Level of Concern': bconcerns,
            'Breeding Season': bbreedingseasons,
        })

        facilitiesdf = pd.DataFrame({
            # 'Land' : lands,
            # 'Acres' : acres, 
        })

        print("DataFrame created.")
        print("Saving DataFrame to CSV...")

         # Create an in-memory bytes buffer
        output = io.BytesIO()
        
        # Use BytesIO object to write the Excel file
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edspeciesdf.to_excel(writer, sheet_name='Endangered Species')
            eaglesdf.to_excel(writer, sheet_name='Bald & Golden Eagles')
            migratorydf.to_excel(writer, sheet_name='Migratory Birds')
            facilitiesdf.to_excel(writer, sheet_name='Facilities')
        
        # Seek to the beginning of the BytesIO object
        output.seek(0)
        
        # Extract the file name from the shapefile path
        shapefile_name = os.path.basename(shapefile_path)
        shapefile_name_without_ext = os.path.splitext(shapefile_name)[0]
        
        # Create a download button with the in-memory file
        st.download_button(
            label="Download Excel file",
            data=output,
            file_name=f"IPaC_{shapefile_name_without_ext}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        

    except Exception as e:
        # Capture any console logs or JavaScript errors
        logs = driver.get_log('browser')
        for log in logs:
            print(log)
        print(f'An error occurred: {str(e)}')
            

    finally:
        driver.quit()
    pass

def click_tab(tab_id):
    try:
        tab = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, tab_id)))
        driver.execute_script("arguments[0].scrollIntoView(true);", tab)  # Scroll into view
        print(f"Trying to click on tab: {tab_id}")
        tab.click()
        print(f"Clicked on tab: {tab_id}")
    except TimeoutException:
        print(f"Timeout waiting for tab: {tab_id} to be clickable")
    except WebDriverException as e:
        print(f"WebDriverException occurred while clicking on tab: {tab_id} - {e}")
        print(f"Attempting to click using JavaScript")
        try:
            driver.execute_script("arguments[0].click();", tab)
            print(f"Clicked on tab using JavaScript: {tab_id}")
        except Exception as js_e:
            print(f"JavaScript click also failed for tab: {tab_id} - {js_e}")

# Main app
def _main():
    hide_streamlit_style = """
    <style>
    # MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)  # This let's you hide the extra branding and menus
    # Add background image from local file
    image_file = "flatirons.JPG"
    add_background_image(image_file)

    # Add title at the top of the screen
    st.title("IPaC Information for Planning and Consultation")

    # Use st.sidebar as a context manager
    with st.sidebar:
        # Display a static image
        st.image('radia-full.png')

        # Convert another image to base64 and display it centered
        bin_str = get_base64_of_bin_file('usfish.png')
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center;">
                <img src="data:image/png;base64,{bin_str}" width="250"/>
            </div>
            """,
            unsafe_allow_html=True
        )

    # page_name = st.sidebar.selectbox(st.image('radia-logo-large.png'), page_names_to_funcs.keys())
    uploaded_file_path = introPage()

    if uploaded_file_path is not None:
        # if uploaded_file_path
        if 'file_processed' not in st.session_state or st.session_state.file_processed != uploaded_file_path:
            # Process the file if not already processed
            st.session_state.file_processed = uploaded_file_path
        # Run Selenium operations
        run_selenium(uploaded_file_path)    

    
        

if __name__ == '__main__':
    _main()
  

