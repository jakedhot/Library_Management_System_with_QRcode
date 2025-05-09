import qrcode
from reedsolo import RSCodec
import json


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

# Define the parameters for Reed-Solomon code (n, k)
n = 15  
k = 10  


qr = qrcode.QRCode(
    version=10,  # Adjust version as needed
    error_correction=qrcode.constants.ERROR_CORRECT_Q,
    box_size=10,
    border=4,
)


qr.add_data(data_json)

# Make the QR code
qr.make(fit=True)


qr_img = qr.make_image(fill_color="black", back_color="white")

# Encode data using Reed-Solomon
rs = RSCodec(n - k)
encoded_data = rs.encode(data_json.encode())


num_modules = qr.version * 4 + 17


for i, bit in enumerate(encoded_data):
    x = i % num_modules
    y = i // num_modules
    qr_img.putpixel((x, y), 255 * (1 - bit))


qr_img.save("test/naa_ra_with_rs.png")

print("QR code with Reed-Solomon error correction saved as 'test/naa_ra_with_rs.png'")
