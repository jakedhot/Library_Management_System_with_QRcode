import qrcode
import json
import reedsolo

# Define parameters for Reed-Solomon encoding
n = 15  # Total number of symbols (data + parity)
k = 6   # Number of data symbols

# Define the data to be encoded

u_name = input('ENTER NAME: ')
usn = input('ENTER Usn: ')
course = input('ENTER Course: ')

data = {
    "name": u_name,
    "usn": usn,
    "course": course
}

# Convert data to JSON format
json_data = json.dumps(data)

# Apply Reed-Solomon encoding
encoder = reedsolo.RSCodec(n - k)
encoded_data = encoder.encode(json_data.encode('utf-8'))

# Create a QR code instance
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)

# Add the Reed-Solomon encoded data to the QR code
qr.add_data(encoded_data)
qr.make(fit=True)

# Create an image from the QR code
qr_image = qr.make_image(fill_color="black", back_color="white")

# Save or display the QR code image
qr_name = input('ENTER QR CODE NAME: ')
qr_image.save(f"qr_code/{qr_name}.png")
qr_image.show()
