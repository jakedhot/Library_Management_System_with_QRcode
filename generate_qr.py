import os
import cv2
import uuid
import json
import qrcode
from reedsolo import RSCodec
from datetime import datetime
from pyzbar.pyzbar import decode
from PIL import Image
import numpy as np

# Function to generate a unique filename
def generate_unique_filename():
    random_string = str(uuid.uuid4().hex)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    filename = f"{timestamp}_{random_string}.png"

    return filename

def generate_qr_code(data, folder):
    # Create the directory if it doesn't exist
    os.makedirs(f"static/img/qr_code/{folder}", exist_ok=True)

    # Convert data to JSON format
    json_data = json.dumps(data)

    # Apply Reed-Solomon encoding
    encoder = RSCodec(2)  # Adjust the number of parity symbols as needed
    encoded_data = encoder.encode(json_data.encode())

    # Create a QR code instance
    qr = qrcode.QRCode(
        version=10,  # Adjust version as needed
        error_correction=qrcode.constants.ERROR_CORRECT_Q,
        box_size=10,
        border=4,
    )

    # Add the encoded data to the QR code
    qr.add_data(encoded_data.decode())  # Decode bytes to string
    qr.make(fit=True)

    # Create an image from the QR code
    qr_name = generate_unique_filename()
    qr_path = os.path.join(f"static/img/qr_code/{folder}", qr_name)
    qr_image = qr.make_image(fill_color="black", back_color="white")

    # Save the QR code image
    qr_image.save(qr_path)

    return qr_name

def generate_student_qr_code(student_fname, student_lname, student_birthdate, student_phone, student_email, student_usn, student_course, student_year):
    data = {
        "Type": "Student",
        "Name": student_fname + " " + student_lname,
        "Birthdate": student_birthdate,
        "Phone": student_phone,
        "Email": student_email,
        "USN": student_usn,
        "Program": student_course,
        "Year": student_year,
    }

    # Convert the data to a JSON string
    json_data = json.dumps(data)

    # Generate the QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json_data)
    qr.make(fit=True)

    # Save the QR code to a file
    img = qr.make_image(fill="black", back_color="white")
    qr_path = f"static/img/qr_codes/students/{student_usn}.png"
    img.save(qr_path)

    return qr_path

def generate_book_qr_code(acc_num, title, author, genre, published_date):
    # Create the data dictionary
    data = {
        "Type": "Book",
        "AccessionNumber": acc_num,
        "BookTitle": title,
        "Author": author,
        "Genre": genre,
        "PublicationYear": published_date,
    }

    # Convert the data to a JSON string
    json_data = json.dumps(data)

    # Generate the QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(json_data)  # Add the JSON data to the QR code
    qr.make(fit=True)

    # Save the QR code to a file
    img = qr.make_image(fill="black", back_color="white")
    qr_path = f"static/img/qr_code/books/{acc_num}.png"  # Save with the accession number as the filename
    img.save(qr_path)

    return qr_path
def decoder(qr_code):
    qr_code_gray = cv2.cvtColor(qr_code, cv2.COLOR_BGR2GRAY)
    decoded_objects = decode(qr_code_gray)

    for obj in decoded_objects:
        barcode_data = obj.data.decode("utf-8")

        if barcode_data:
            try:
                # Attempt to parse the data as JSON
                decoded_data = json.loads(barcode_data)

                # Validate the decoded data
                if 'Type' not in decoded_data or decoded_data['Type'] not in ['Student', 'Book']:
                    return 'Invalid QR Code Format: Missing or invalid "Type" field.'

                return decoded_data
            except json.JSONDecodeError:
                return 'Invalid QR Code Format: Data is not valid JSON.'

    return 'QR Code Not Recognized. Please try again.'