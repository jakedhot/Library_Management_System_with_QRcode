import qrcode

def generate_qr_code(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    return img

data = {'Type': 'Student', 'Name': 'Nas Jay Saladaga', 'Email': 'vjrecilla.aclcbxu@gmail.com', 'USN': '18224554900', 'Phone': '094595161512', 'Program': 'Secret', 'Year': '4'}

# Generate data string
data_str = '\n'.join([f"{key}: {value}" for key, value in data.items()])

# Generate QR code
qr_code = generate_qr_code(data_str)

# Save QR code to a file
qr_code.save("test/student_qr_code.png")
print("QR code generated successfully!")
