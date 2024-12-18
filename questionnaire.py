import streamlit as st
import streamlit_survey as ss
import random
import requests
import base64
import traceback
import piexif
from streamlit_js_eval import get_geolocation, streamlit_js_eval
import logging
from PIL import Image
from streamlit_modal import Modal


# Road Distress Knowledge Test Questions
ROAD_DISTRESS_QUESTIONS = {
    "multiple_choice": [
        {
            "question": "What is the primary purpose of road distress mapping?",
            "options": [
                "Urban planning",
                "Infrastructure maintenance",
                "Traffic management",
                "Road safety improvement",
                "Environmental monitoring"
            ]
        },
        {
            "question": "Which factor most significantly contributes to road surface deterioration?",
            "options": [
                "Heavy vehicle traffic",
                "Climate conditions",
                "Poor initial construction",
                "Lack of maintenance",
                "Inadequate drainage systems"
            ]
        },
        {
            "question": "What is the most critical tool for accurate road distress surveying?",
            "options": [
                "GPS technology",
                "High-resolution camera",
                "Measuring tape",
                "Drone imagery",
                "Machine learning algorithms"
            ]
        },
        {
            "question": "What type of road distress is most commonly associated with climate change?",
            "options": [
                "Potholes",
                "Rutting",
                "Thermal cracking",
                "Edge deterioration",
                "Surface bleeding"
            ]
        },
        {
            "question": "What is the primary benefit of regular road condition surveys?",
            "options": [
                "Cost reduction",
                "Improved road safety",
                "Better urban planning",
                "Enhanced driver comfort",
                "Efficient resource allocation"
            ]
        }
    ],
    "descriptive": [
        "Describe the process you would follow to document and report a road distress point.",
        "Explain the importance of accurately capturing GPS coordinates during road condition surveys.",
        "How can technology improve road maintenance strategies?",
        "Discuss the environmental impact of poor road maintenance.",
        "What challenges do urban areas face in maintaining road infrastructure?"
    ]
}

IMAGE_URLS = [
    "https://i.ibb.co.com/LSGcVQJ/IMG-20240909-184513.jpg",
    "https://i.ibb.co.com/YBtzHgP/fba5fc873b15.jpg",
    "https://i.ibb.co.com/0rQQ7pg/IMG-20240909-185135.jpg",
    "https://i.ibb.co.com/LNLC7H8/IMG-20240909-183909.jpg",
    "https://i.ibb.co.com/NC54D3V/20240909-181409.jpg",
    "https://i.ibb.co.com/4RX2Zjt/20240909-180301.jpg",
    "https://i.ibb.co.com/SQTBYnp/20240909-181957.jpg",
    "https://i.ibb.co.com/SN6g29W/20240909-182826.jpg",
    "https://i.ibb.co.com/hMPNgy8/20240909-175940.jpg",
    "https://i.ibb.co.com/Dbb4F47/20240909-180803.jpg",
    "https://i.ibb.co.com/D13Yz79/PXL-20240913-140209823.jpg",
    "https://i.ibb.co.com/GHJRKy8/PXL-20240913-130058489.jpg"
]

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("road_distress_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_random_questions_and_images():
    # Initialize session state if not exists
    if 'multiple_choice_questions' not in st.session_state:
        # Seed randomization
        random.seed()

        # Random Multiple Choice Questions
        st.session_state.multiple_choice_questions = random.sample(
            ROAD_DISTRESS_QUESTIONS['multiple_choice'], 3)

        # Random Descriptive Questions
        st.session_state.descriptive_questions = random.sample(
            ROAD_DISTRESS_QUESTIONS['descriptive'], 2)

        # Random Image URLs
        st.session_state.selected_images = random.sample(IMAGE_URLS, 4)

    # Return stored questions and images
    return (
        st.session_state.multiple_choice_questions,
        st.session_state.descriptive_questions,
        st.session_state.selected_images
    )


def upload_image_to_imgbb(uploaded_file):
    """Upload image to ImgBB"""
    try:
        #imgbb_api_key = st.secrets.get("IMGBB_API_KEY", "your_api_key")
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": "64869f569c72df2121fa2640ae4b3d1f",
            "image": base64.b64encode(uploaded_file.getvalue()).decode('utf-8')
        }
        response = requests.post(url, payload)
        return response.json()['data']['url'] if response.ok else None
    except Exception as e:
        st.error(f"Image upload error: {e}")
        return None


# GPS Coordinate Extraction Functions
def extract_gps_from_image(image):
    try:
        logger.info("Starting GPS extraction from image")
        
        img = Image.open(image)
        logger.info(f"Image opened successfully. Format: {img.format}, Mode: {img.mode}, Size: {img.size}")
        
        try:
            # Use piexif to load EXIF data
            exif_dict = piexif.load(img.info.get('exif', b''))
            logger.info("EXIF data extracted successfully")
            
            # Check if GPS data exists
            gps_ifd = exif_dict.get('GPS', {})
            
            if (piexif.GPSIFD.GPSLatitude in gps_ifd and 
                piexif.GPSIFD.GPSLongitude in gps_ifd):
                
                gps_info = {
                    'latitude': gps_ifd.get(piexif.GPSIFD.GPSLatitude),
                    'latitude_ref': gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef),
                    'longitude': gps_ifd.get(piexif.GPSIFD.GPSLongitude),
                    'longitude_ref': gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
                }
                
                logger.info(f"GPS Info extracted: {gps_info}")
                return gps_info
            else:
                logger.warning("No GPS information found in EXIF data")
                return None
        
        except Exception as exif_error:
            logger.error(f"Error extracting EXIF data: {exif_error}")
            logger.error(traceback.format_exc())
            return None
    
    except Exception as e:
        logger.error(f"Critical error in GPS extraction: {e}")
        logger.error(traceback.format_exc())
        return None

def dms_to_decimal(coords, ref):
    if not coords or not ref:
        return None
    
    try:
        # Unpack the coordinate tuple
        degrees = coords[0][0] / coords[0][1]  # First tuple is degrees
        minutes = coords[1][0] / coords[1][1]  # Second tuple is minutes
        seconds = coords[2][0] / coords[2][1]  # Third tuple is seconds
        
        # Convert to decimal
        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
        
        # Apply sign based on reference
        if ref in [b'S', b'W', 'S', 'W']:
            decimal = -decimal
        
        return decimal
    except Exception as conv_error:
        logger.error(f"Coordinate conversion error: {conv_error}")
        logger.error(f"Coordinates: {coords}, Reference: {ref}")
        logger.error(traceback.format_exc())
        return None

def convert_gps_to_decimal(gps_coords):
    if not gps_coords:
        logger.warning("No GPS coordinates provided for conversion")
        return None, None
    
    try:
        logger.info("Starting GPS coordinate conversion")
        
        # Convert latitude and longitude
        latitude = dms_to_decimal(
            gps_coords.get('latitude'), 
            gps_coords.get('latitude_ref')
        )
        longitude = dms_to_decimal(
            gps_coords.get('longitude'), 
            gps_coords.get('longitude_ref')
        )
        
        logger.info(f"Converted Coordinates - Lat: {latitude}, Lon: {longitude}")
        
        return latitude, longitude
    
    except Exception as e:
        logger.error(f"Error converting GPS coordinates: {e}")
        logger.error(traceback.format_exc())
        
        return None, None
    
def capture_image_location(captured_image):
    
    try:
        # Attempt to get geolocation
        location = get_geolocation()
        
        if location and 'coords' in location:
            # Extract coordinates from the nested structure
            coords = location['coords']
            latitude = coords.get('latitude')
            longitude = coords.get('longitude')
            accuracy = coords.get('accuracy')
            
            # Display location details
            #st.success(f"Location Captured with Image:")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Latitude", f"{latitude:.6f}")
            
            with col2:
                st.metric("Longitude", f"{longitude:.6f}")
            
            with col3:
                st.metric("Accuracy", f"{accuracy:.2f} meters")
            
            return latitude, longitude
        else:
            st.warning("Getting location from image 🛠️")
            return None, None
    
    except Exception as e:
        st.error(f"Location capture error: {e}")
        return None, None



    with st.expander("Join the Road Revolution! 🚗✨", expanded=True):
        st.markdown(""" 
                    
        🌟 **Make a Difference Today!** 
        Your observations can help build safer, smoother roads for Rajshahi City. 
        
        🛠️ **No Expertise? No Problem!** 
        Our tool is easy to use—just observe, record, and submit! 
        
        🌍 **Be Part of the Change** 
        Your contributions will shape better road networks and empower citizen-led solutions. 
        
        📊 **Access the Data** 
        All collected data will be publicly available for research and policy improvements. 
        
        🚀 **Click to Start Your Journey!** 
        Let's transform our roads together! 
        """)

def show_welcome_dialog():
    # Create an expander with the initial welcome message
    with st.expander("Join the Road Revolution! 🚗✨", expanded=True):
        st.markdown("""
        
        🌟 **Make a Difference Today!** 
        Your observations can help build safer, smoother roads for Rajshahi City. 
        
        🛠️ **No Expertise? No Problem!** 
        Our tool is easy to use—just observe, record, and submit! 
        
        🌍 **Be Part of the Change** 
        Your contributions will shape better road networks and empower citizen-led solutions. 
        
        📊 **Access the Data** 
        All collected data will be publicly available for research and policy improvements. 
        
        🚀 **Click to Start Your Journey!** 
        Let's transform our roads together! 
        """)
        
        read_more = st.button("Read More")
        
        # Detailed introduction when Read More is clicked
        if read_more:
            st.markdown("""
            ## **Introduction**
            Hello! We are **Bipul Dey and Towhidul Islam**, students of the **Urban and Regional Planning Department at RUET**. We are conducting an important study to map and analyze road distress points in **Rajshahi City**. Road distress refers to specific damages such as potholes, cracks, and surface wear that make roads unsafe and inconvenient for use.

            To make our roads better, we've developed a **simple tool** that allows anyone—regardless of their knowledge about road engineering—to help us collect valuable data on road distress points.

            We believe that **citizen participation** can transform how road monitoring is done, and your contribution can lead to a safer, more efficient road network for all.

            ## **What Are Road Distress Points?**
            We are focusing on five types of distress points commonly found on roads:

            1. **Potholes**: Small, bowl-shaped holes in the road caused by wear and water damage.
               * *Example*: Those annoying bumps your car jolts over during your daily commute.

            2. **Patching**: Repairs made to the road but often uneven or poorly done.
               * *Example*: The bumpy patchwork that creates discomfort while driving.

            3. **Raveling**: Gradual wearing away of the road surface, leaving loose gravel or cracks.
               * *Example*: A rough, pebbly road surface where tires lose grip.

            4. **Edge Cracks**: Long cracks forming along the sides of the road.
               * *Example*: The broken road edges that make walking or cycling unsafe.

            5. **Narrow and Wide Cracks**: Small or large splits in the road, often leading to larger problems.
               * *Example*: Fine cracks that eventually grow into potholes if left untreated.

            By identifying and recording these issues, we can prioritize repairs, improve road safety, and reduce vehicle wear-and-tear.

            ## **How You Can Participate**
            We've made it easy for anyone to contribute!

            1. **Step 1: Use Our Tool**
               * Our tool is simple to use and requires no technical knowledge. You only need to observe and record the distress points using your phone or device.

            2. **Step 2: Follow the Guidelines**
               * Read our clear descriptions of distress points (potholes, patching, etc.) to identify them correctly.
               * Use the tool to mark their locations on the map and add brief descriptions.

            3. **Step 3: Submit Your Data**
               * Once done, submit your observations. It's that easy!

            ## **Why Should You Participate?**
            1. **Transform Roads in Rajshahi City**: Your efforts will directly help in identifying problem areas, ensuring timely repairs, and creating safer roads for everyone.

            2. **Be a Part of Innovation**: By participating, you're contributing to a revolutionary road monitoring process that empowers citizens and integrates them into urban planning.

            3. **Access to Public Data**: All data collected will be made **publicly available** for visualization, further study, and policymaking.
               * *Example*: Researchers, policymakers, or even concerned citizens can use the database to analyze trends and propose solutions.

            4. **Shape the Future of Road Networks**: Your contribution will not only improve today's roads but also set a precedent for smarter, citizen-focused road management systems.

            ## **Conclusion**
            This project is more than a study—it's a chance for every resident of Rajshahi City to contribute to the betterment of their community. Together, we can create a safer, more efficient road network that serves everyone.

            **Join us in this mission to revolutionize road monitoring through the power of citizen participation.**

            Let's pave the way—literally and figuratively—for a better future!
            """)


def main():
    st.set_page_config(
        page_title="Road Distress Surveyor Application", page_icon=":world_map:")

    # Check if this is the first time the app is opened
    if 'first_visit' not in st.session_state:
        st.session_state.first_visit = True

    # Show welcome dialog if it's the first visit
    if st.session_state.first_visit:
        show_welcome_dialog()
        
    # Initialize survey with 4 pages and progress bar
    survey = ss.StreamlitSurvey("Road Distress Surveyor Application")
    
    # Retrieve pre-selected random questions and images
    multiple_choice_questions, descriptive_questions, selected_images = get_random_questions_and_images()
    
    # Use st.session_state to store form_data if not exists
    if 'form_data' not in st.session_state:
        st.session_state.form_data = {}
        
    # Create pages
    pages = survey.pages(3, progress_bar=True, on_submit=lambda: handle_submission(survey))

    with pages:
        # Page 1: Personal and Contact Information
        if pages.current == 0:
            st.title("Personal and Contact Information")

            # Personal Information
            st.subheader("Personal Information")

            name = st.text_input("Full Name")
            st.session_state.form_data['name'] = name

            age = st.number_input(
                "Age",
                min_value=16,
                max_value=80,
                help="You must be at least 16 years old"
            )
            st.session_state.form_data['age'] = age

            education_type = st.selectbox(
                "Current Education/Work Status",
                ["University", "College", "School",
                    "Working Professional", "Other"]
            )
            st.session_state.form_data['education_type'] = education_type

            # Conditional Education Fields
            if education_type == "University":
                university = st.text_input("University Name")
                st.session_state.form_data['university'] = university

                department = st.text_input("Department")
                st.session_state.form_data['department'] = department

            elif education_type == "College":
                college = st.text_input("College Name")
                st.session_state.form_data['college'] = college

            elif education_type == "School":
                school = st.text_input("School Name")
                st.session_state.form_data['school'] = school

            # Contact Information
            st.subheader("Contact Information")

            email = st.text_input("Email Address")
            st.session_state.form_data['email'] = email

            phone = st.text_input("Phone Number")
            st.session_state.form_data['phone'] = phone

        # Page 2: Road Distress Knowledge Test
        elif pages.current == 1:
            st.title("Road Distress Knowledge Test")

            # Multiple Choice Questions
            st.subheader("Multiple Choice Questions")
            st.session_state.form_data['multiple_choice_answers'] = {}
            for q in multiple_choice_questions:
                answer = st.radio(q['question'], options=q['options'])
                st.session_state.form_data['multiple_choice_answers'][q['question']] = answer

            # Descriptive Questions
            st.subheader("Descriptive Questions")
            st.session_state.form_data['descriptive_answers'] = {}
            for q in descriptive_questions:
                answer = st.text_area(q)
                st.session_state.form_data['descriptive_answers'][q] = answer

        # Page 3: Image and GPS Test
        elif pages.current == 2:
            st.title("Image and GPS Test")

            # Image Identification Section
            st.subheader("Road Distress Image Identification")

            # Create two columns for images
            cols = st.columns(2)

            # Store image assessments
            st.session_state.form_data['image_assessments'] = {}

            # Iterate through selected images
            for i, image_url in enumerate(selected_images):
                # Alternate between left and right columns
                col = cols[i // 2]

                with col:
                    # Display image
                    cdn_url = image_url.replace(
                        "https://i.ibb.co.com/", "https://7fsm51mk.dev.cdn.imgeng.in/")
                    st.image(cdn_url, use_column_width=True)

                    # Create a unique key for each image
                    image_key = f"image_assessment_{i}"

                    # Distress Type Dropdown
                    distress_type = st.selectbox(
                        f"What type of road distress do you see in Image {i+1}?",
                        ["Pothole", "Patching", "Raveling",
                            "Crack", "Edge Crack", "Others"],
                        key=image_key + "_type"
                    )

                    # Severity Slider
                    severity = st.slider(
                        f"Rate the severity of the distress in Image {i+1}",
                        min_value=1,
                        max_value=5,
                        key=image_key + "_severity",
                        help="1 = Minimal, 5 = Severe"
                    )

                    # Store assessment in session state
                    st.session_state.form_data['image_assessments'][image_key] = {
                        'image_url': image_url,
                        'distress_type': distress_type,
                        'severity': severity
                    }
            st.divider()

            # GPS and Image Upload Section
            st.subheader("GPS and Image Upload")

            # Location Method
            location_method = st.radio(
                "How would you provide GPS coordinates?",
                ["Upload Image with GPS", "Capture Image"],
                key="location_method_radio"
            )
            st.session_state.form_data['location_method'] = location_method

            # Image Upload
            if location_method == "Upload Image with GPS":
                uploaded_image = st.file_uploader(
                    "Upload Image", type=['jpg', 'jpeg', 'png'], key="gps_image_uploader")
                if uploaded_image:
                    uploaded_image_url = upload_image_to_imgbb(uploaded_image)
                    st.toast('Image uploaded successfully', icon='✅')
                    st.session_state.form_data['uploaded_image_url'] = uploaded_image_url
                    try:
                        gps_data = extract_gps_from_image(uploaded_image)

                        if gps_data:
                            latitude, longitude = convert_gps_to_decimal(gps_data)
                            if latitude and longitude:
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.metric("Latitude", f"{latitude:.6f}")
                                with col2:
                                    st.metric("Longitude", f"{longitude:.6f}")
        
                                # Store coordinates in session state
                                st.session_state.form_data['gps_coords'] = {
                                    'latitude': latitude,
                                    'longitude': longitude
                                }
                        else:
                            st.warning("No GPS data found in the image", icon="🚨")
            
                    except Exception as e:
                        st.error(f"Error processing image: {e}")
                        # Log the full traceback
                        st.error(traceback.format_exc())
            else:
                captured_image = st.camera_input(
                    "Capture Image", key="camera_input")
                if captured_image:
                    try:
                        latitude, longitude = capture_image_location(captured_image)
                        st.session_state.form_data['gps_coords'] = {
                            'latitude': latitude,
                            'longitude': longitude
                        }
                    except Exception as gps_error:
                        st.error(f"GPS capture error: {gps_error}")
                        
                    captured_image_url = upload_image_to_imgbb(captured_image)
                    st.toast("Image captured and uploaded successfully", icon='✅')
                    st.session_state.form_data['captured_image_url'] = captured_image_url

            # Distress Point Assessment
            distress_type = st.selectbox(
                f"Type of Road Distress",
                ["Pothole", "Patching", "Raveling",
                            "Crack", "Edge Crack", "Others"],
                key="distress_type"
            )
            st.session_state.form_data['distress_type'] = distress_type

            distress_severity = st.slider(
                "Rate the severity of the distress",
                min_value=1, max_value=5,
                help="1 = Minimal, 5 = Severe",
                key="distress_severity_slider"
            )
            st.session_state.form_data['distress_severity'] = distress_severity


def handle_submission(survey):
    """Handle form submission"""
    form_data = st.session_state.form_data
    st.write(form_data)

    # Save form data to Google Sheets


if __name__ == "__main__":
    main()
