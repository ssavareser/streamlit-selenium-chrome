import streamlit as st

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
    return webdriver.Chrome(
        service=Service(
            ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
        ),
        options=options,
    )

    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--headless")
    
    driver = get_driver()
    driver.get("https://ipac.ecosphere.fws.gov/location/index")
  

