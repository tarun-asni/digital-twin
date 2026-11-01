
Project Setup Guide: Digital Twin 
# Step 1: Clone the Repository
Open your terminal and run:
    git clone https://github.com/prashantmp/digital-twin.git <br />
    cd digital-twin
# Step 2: Checkout to the Required Branch
    git checkout zoneMonitorOnnx 
This branch contains the ONNX-based detection logic and zone monitoring implementation.
# Step 3: 
    # Install Dependencies
        Use a Virtual Environment 
        python3 -m venv objvenv
        source objvenv/bin/activate     (Mac)
        objvenv\Scripts\activate        (Windows)

    # Install Required Packages
    pip install --upgrade pip
    pip install -r requirements.txt
    
    If requirements.txt is missing, install dependencies manually:
    
    pip install opencv-python numpy onnxruntime
    pip install matplotlib requests
# Step 4: Detection Model Path
The detection logic using the ONNX model is located in: <br />
    mediahub/scripts/ <br />
The main detection script is:
    mediahub/scripts/main.py
# Step 5: Run the Project
Open the project in VS Code or your terminal and run: <br />
    python mediahub/scripts/main.py <br />
Your webcam will start immediately. <br />
   Usage Instructions<br />
  There are 2 possible scenarios once the webcam feed starts:<br />
  1. Click two points on the webcam feed:<br />
	- One on the top-left. <br />
	- One on the bottom-right. <br />
	- Then press 'q' to begin detection with a restricted zone. <br />
  2. Press 'q' immediately to begin detection without setting a restricted zone.<br />
  3. To stop the detection and close the webcam, press 'q' again.<br />
 
