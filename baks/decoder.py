import cv2
from pyzbar.pyzbar import decode
import reedsolo
import json

# Define parameters
n = 15  # Total number of symbols (data + parity)
k = 6   # Number of data symbols

# Read the QR code image
file = input('ENTER FILE: ')
qr_code_image = cv2.imread(f'static/img/qr_code/students/20240405174635_36bf82c70bd245aababad695b463c10e.png', cv2.IMREAD_GRAYSCALE)

# Decode the QR code image
decoded_objects = decode(qr_code_image)

if decoded_objects:
    qr_data = decoded_objects[0].data
    # print("QR code data:", qr_data)  # Print the extracted data

    try:
        # Convert bytes to string
        qr_data_str = qr_data.decode('utf-8')

        # Extract valid JSON part from the string
        json_start = qr_data_str.find('{')
        json_end = qr_data_str.rfind('}') + 1
        valid_json_str = qr_data_str[json_start:json_end]

        # Load JSON data
        decoded_data = json.loads(valid_json_str)

        # Print the decoded data
        print("Decoded data:", decoded_data)

        # Extract only desired fields (name, usn, and course)
        extracted_data = {key: decoded_data[key] for key in ['name', 'usn', 'course']}
        print("Extracted data:", extracted_data)
    except json.JSONDecodeError as e:
        print("Error decoding JSON data:", e)
    except IndexError:
        print("No QR code found in the image.")
