import qrcode
from reedsolo import RSCodec
import json

# Define the parameters for Reed-Solomon code (n, k)
n = 40  
k = 20 

data_dict = {
    'Type': 'Student',
    'Name': 'Nas Jay Saladaga',
    'Email': 'vjrecilla.aclcbxu@gmail.com',
    'USN': '18224554900',
    'Phone': '094595161512',
    'Program': 'Secret',
    'Year': '4'
}

# Convert dictionary to JSON string
data_json = json.dumps(data_dict)


qr = qrcode.QRCode(
    version=15, 
    error_correction=qrcode.constants.ERROR_CORRECT_L, 
    box_size=10,  
    border=4, 
)

# Add data to the QR code
qr.add_data(data_json)

# Make the QR code
qr.make(fit=True)

# Get the image
qr_img = qr.make_image(fill_color="black", back_color="white")

# Save the QR code as an image file
qr_img.save("test/naa_ra.png")

# Print a message indicating where the QR code image is saved
print("QR code saved as 'test/naa_ra.png'")