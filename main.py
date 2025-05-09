from flask import Flask, render_template, url_for, request, redirect, flash, session, Response
from pyzbar.pyzbar import decode,ZBarSymbol
from flask_mysqldb import MySQLdb
from functools import wraps
import cv2
import os
import uuid
from db import create_db, DB_HOST, DB_USER, DB_PW, DB_NAME
from generate_qr import generate_student_qr_code, generate_book_qr_code, decoder
from flask import current_app
from flask import render_template, request
import json
from flask_socketio import SocketIO
from datetime import datetime, timedelta
from contextlib import contextmanager
import qrcode
from werkzeug.utils import secure_filename


import socketio
import numpy as np



app = Flask(__name__)
app.secret_key = "uwu"
sio = socketio.Server(async_mode='threading')
app.wsgi_app = socketio.WSGIApp(sio, app.wsgi_app)
# Allowed file extensions for student pictures
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configure upload folder for student pictures
UPLOAD_FOLDER = 'static/img/students_image/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Function to check if a filename has an allowed extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
def preprocess_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return thresh

def decode_barcode(frame):
    processed_frame = preprocess_frame(frame)
    try:
        decoded_objects = decode(processed_frame, symbols=[ZBarSymbol.PDF417])
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            print("Decoded data:", data)
            return data
    except Exception as e:
        print("Error decoding barcode:", e)
        return None
# Function to check if an email domain is allowed
def is_allowed_domain(email):
    allowed_domains = ['example.com', 'school.edu']  # Add your allowed domains here
    domain = email.split('@')[-1]
    return domain in allowed_domains
@contextmanager
def get_db_connection():
    """
    A context manager for handling database connections.
    Automatically closes the connection after use.
    """
    conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, password=DB_PW, db=DB_NAME)
    try:
        yield conn  # Provide the connection to the caller
    finally:
        conn.close()  # Ensure the connection is closed


socketio = SocketIO(app)
with app.app_context():
    print(current_app.name)
create_db()

def login_required(route):
    @wraps(route)   
    def wrap(*args, **kwargs):
        if 'logged' in session:
            return route(*args, **kwargs)
        else:
            return render_template('index.html')
    return wrap

def connection():
    try:
        conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, password=DB_PW, db=DB_NAME)
        return conn
    except Exception as e:
        return str(e)



@app.route('/generate_frames_students', methods=['GET', 'POST'])
def generate_frames_students():
    # Initialize the camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera.")
        return "Camera not available", 500

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            break

        # Decode the QR code in the frame
        qr_data = decoder(frame)

        # If QR code is detected, emit the data via Socket.IO
        if qr_data and isinstance(qr_data, dict):
            socketio.emit('qr_data', qr_data, namespace='/test')  # Emit QR data to the client
            print("QR Code Detected:", qr_data)

        # Encode the frame as JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            print("Error: Failed to encode frame.")
            break

        # Convert the frame to bytes
        frame_bytes = buffer.tobytes()

        # Yield the frame for streaming
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    # Release the camera when done
    cap.release()
    print("Camera released.")

@socketio.on('connect', namespace='/test')
def test_connect():
    print('Client connected')

@app.route('/display_data', methods=['GET', 'POST'])
def display_data():
    # data =session['qr_data']
    # print(data)
    return render_template('test.html')

@app.route('/video_feed_students')
def video_feed():
    return Response(generate_frames_students(), mimetype='multipart/x-mixed-replace; boundary=frame')
@sio.on('start_camera')
def start_camera(sid):
    print("Camera started")

@sio.on('stop_camera')
def stop_camera(sid):
    print("Camera stopped")

@app.route('/borrow', methods=['GET', 'POST'])
def borrow():
    try:
        conn = connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    borrowed.*,
                    students.*,
                    books.*
                FROM
                    borrowed
                INNER JOIN
                    students ON borrowed.student_id = students.student_id
                INNER JOIN
                    books ON borrowed.book_id = books.book_id
                WHERE
                    borrowed.status_id != 3;
            """)
            borrows = cur.fetchall()
        return render_template('borrowed.html', borrow=borrows)
    except Exception as e:
        print(f"Error fetching borrowed books: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching borrowed books'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/success')
def success_page():
    return "Success! QR data processed."

# Route to start a new video feed
@app.route('/start_video_feed')
def start_video_feed():
    # Here you can include any code to start a new video feed
    # For example, you can call the generate_frames() function
    return Response(generate_frames_students(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'logged' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')
# @app.route('/')
# def index():
#     # Pass the video feed URL to the template
#     return render_template('index.html', video_feed_url=url_for('video_feed'))

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    conn = connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT COUNT(*) AS num_available_books
                FROM books
                WHERE status_id = (SELECT status_id FROM status WHERE status_name = 'Available');
            """)
        available_books = cur.fetchall()[0][0]

        cur.execute("SELECT COUNT(*) FROM borrowed")
        all_books = cur.fetchall()[0][0]

        cur.execute("SELECT COUNT(*) FROM returned")
        returned_books = cur.fetchall()[0][0]
    conn.close()
    return render_template('dashboard.html', available_books=available_books, all_books=all_books, returned_books=returned_books)

@app.route('/scan_qr', methods=['POST'])
@login_required
def scan_qr():
    qr_code = request.files['qr_code']
    decoded_data = decoder(qr_code)
    
    if isinstance(decoded_data, str):
        return jsonify({'error': decoded_data})
    
    return jsonify(decoded_data)

@app.route('/transactions', methods=['GET', 'POST'])
@login_required
def transactions():
    return render_template('transactions.html')

@app.route('/try', methods=['GET', 'POST'])
@login_required
def comparing():
    return render_template('comparing.html')

from datetime import datetime, timedelta

@app.route('/process_transaction', methods=['POST'])
def process_transaction():
    conn = None
    try:
        # Get JSON data from the request
        data = request.get_json()
        print("Received data:", data)  # Log the incoming data for debugging

        # Validate the request data
        if not data or 'student' not in data or 'book' not in data or 'action' not in data:
            return jsonify({'success': False, 'message': 'Invalid request: Missing or malformed data'}), 400

        # Extract student, book, and action data
        student_data = data['student']
        book_data = data['book']
        action = data['action']

        # Validate student data
        if student_data.get('Type') != 'Student' or 'USN' not in student_data:
            return jsonify({'success': False, 'message': 'Invalid Student QR Code: Missing or invalid data'}), 400

        # Validate book data
        if book_data.get('Type') != 'Book' or 'AccessionNumber' not in book_data:
            return jsonify({'success': False, 'message': 'Invalid Book QR Code: Missing or invalid data'}), 400

        # Establish a database connection
        conn = connection()
        if not conn:
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500

        # Fetch student ID from the database
        with conn.cursor() as cur:
            cur.execute("SELECT student_id FROM students WHERE student_usn = %s", (student_data['USN'],))
            student_id_result = cur.fetchone()
            if not student_id_result:
                return jsonify({'success': False, 'message': 'Student not found in the system'}), 404
            student_id = student_id_result[0]

        # Fetch book ID from the database
        with conn.cursor() as cur:
            cur.execute("SELECT book_id FROM books WHERE accession_number = %s", (book_data['AccessionNumber'],))
            book_id_result = cur.fetchone()
            if not book_id_result:
                return jsonify({'success': False, 'message': 'Book not found in the system'}), 404
            book_id = book_id_result[0]

        # Process the action (borrow or return)
        if action == 'borrow':
            # Check if the book is already borrowed
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM borrowed WHERE book_id = %s AND status_id != 3", (book_id,))
                if cur.fetchone():
                    return jsonify({'success': False, 'message': 'Book is already borrowed'}), 400

            # Insert into borrowed table
            borrow_date = datetime.now().date()
            return_date = borrow_date + timedelta(days=-1)  # Set return date to 7 days from now
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO borrowed (student_id, book_id, borrow_date, return_date, status_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (student_id, book_id, borrow_date, return_date, 1))  # status_id = 1 (Borrowed)
                conn.commit()

            # Update book status to "Borrowed" (status_id = 2)
            with conn.cursor() as cur:
                cur.execute("UPDATE books SET status_id = 2 WHERE book_id = %s", (book_id,))
                conn.commit()

            return jsonify({'success': True, 'message': 'Book borrowed successfully.'}), 200

        elif action == 'return':
            # Check if the book is currently borrowed
            with conn.cursor() as cur:
                cur.execute("SELECT borrow_id FROM borrowed WHERE book_id = %s AND status_id != 3", (book_id,))
                borrow_id_result = cur.fetchone()
                if not borrow_id_result:
                    return jsonify({'success': False, 'message': 'Book is not currently borrowed'}), 400
                borrow_id = borrow_id_result[0]

            # Insert into returned table
            date_returned = datetime.now().date()
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO returned (borrow_id, return_date, late_fee)
                    VALUES (%s, %s, %s)
                """, (borrow_id, date_returned, 0))  # fine = 0 (no fine)
                conn.commit()

            # Update book status to "Available" (status_id = 1)
            with conn.cursor() as cur:
                cur.execute("UPDATE books SET status_id = 1 WHERE book_id = %s", (book_id,))
                conn.commit()

            # Update borrowed status to "Returned" (status_id = 3)
            with conn.cursor() as cur:
                cur.execute("UPDATE borrowed SET status_id = 3 WHERE borrow_id = %s", (borrow_id,))
                conn.commit()

            return jsonify({'success': True, 'message': 'Book returned successfully.'}), 200

        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400

    except Exception as e:
        print(f"Error processing transaction: {str(e)}")  # Log the error for debugging
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()  # Close the database connection

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

@app.route('/process_return', methods=['POST'])
def process_return():
    conn = None
    try:
        data = request.get_json()
        if not data or 'Type' not in data:
            return jsonify({'error': 'Invalid request: Missing or malformed data'}), 400

        conn = connection()
        if not conn:
            return jsonify({'error': 'Database connection failed'}), 500

        if data['Type'] == 'Book':
            if 'AccessionNumber' not in data:
                return jsonify({'error': 'Invalid Book QR Code: Missing Accession Number'}), 400

            # Check if the student data is in the session
            if 'student' not in session:
                return jsonify({'error': 'Waiting for student data. Please scan the student QR code first.'}), 400

            # Retrieve student data from the session
            student_info = session['student']
            session.pop('student', None)  # Clear student data from session after use

            # Fetch student and book IDs
            with conn.cursor() as cur:
                cur.execute("SELECT student_id FROM students WHERE student_usn = %s", (student_info['USN'],))
                student_id_result = cur.fetchone()
                if not student_id_result:
                    return jsonify({'error': 'Student not found in the system'}), 404
                student_id = student_id_result[0]

                cur.execute("SELECT book_id FROM books WHERE accession_number = %s", (data['AccessionNumber'],))
                book_id_result = cur.fetchone()
                if not book_id_result:
                    return jsonify({'error': 'Book not found in the system'}), 404
                book_id = book_id_result[0]

            # Check if the book is borrowed
            with conn.cursor() as cur:
                cur.execute("SELECT borrow_id FROM borrowed WHERE book_id = %s AND status_id != 3", (book_id,))
                borrow_id_result = cur.fetchone()
                if not borrow_id_result:
                    return jsonify({'error': 'Book is not currently borrowed'}), 400
                borrow_id = borrow_id_result[0]

            # Get the current date
            date_returned = datetime.now().date()

            # Insert the return transaction
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO returned (borrow_id, return_date, late_fee)
                    VALUES (%s, %s, %s)
                """, (borrow_id, date_returned, 0))
                conn.commit()

                # Update the book status to "Available" (status_id = 1)
                cur.execute("UPDATE books SET status_id = 1 WHERE book_id = %s", (book_id,))
                conn.commit()

                # Update the borrowed status to "Returned" (status_id = 3)
                cur.execute("UPDATE borrowed SET status_id = 3 WHERE borrow_id = %s", (borrow_id,))
                conn.commit()

            return jsonify({'message': 'Book returned successfully.'}), 200

        else:
            return jsonify({'error': 'Invalid QR Code: Unrecognized type'}), 400

    except Exception as e:
        print(f"Error processing return: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/students', methods=['GET', 'POST'])
@login_required
def students():
    try:
        conn = connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM students")
            students = cur.fetchall()
        conn.close()

        return render_template('students.html', students=students)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('dashboard'))

@app.route('/digicard', methods=['GET', 'POST'])
@login_required
def digicard():
    return render_template('digicard.html')



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Fetch user information from the database
    user_id = session.get('user_id')  # Get the logged-in user's ID from the session
    if not user_id:
        flash("User not logged in.", "error")
        return redirect(url_for('index'))

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
                user_info = cur.fetchone()  # Fetch the user's data

        if not user_info:
            flash("User not found.", "error")
            return redirect(url_for('index'))

        # Render the profile template with the user's information
        return render_template('profile.html', user=user_info)

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('index'))

@app.route('/result', methods=['GET', 'POST'])
@login_required
def result():
    return render_template('digicardresult.html')

@app.route('/return_books', methods=['GET', 'POST'])
@login_required
def return_books():
    conn = connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT r.return_id, r.return_date, r.late_fee,
                   b.borrow_date, b.return_date,
                   s.student_fname,s.student_lname, s.student_email,
                   bk.book_title, bk.author
            FROM returned r
            JOIN borrowed b ON r.borrow_id = b.borrow_id
            JOIN students s ON b.student_id = s.student_id
            JOIN books bk ON b.book_id = bk.book_id;
            """)
        returned_books = cur.fetchall()

    conn.close()
    return render_template('return_books.html', returned_books = returned_books)

@app.route('/books_available', methods=['GET', 'POST'])
@login_required
def books_available():
    conn = connection()

    cursor = conn.cursor()
    cursor.execute("""
    SELECT
        books.*,
        status.status_name AS status
    FROM
        books
    INNER JOIN
        status ON books.status_id = status.status_id;
""")
    available_books = cursor.fetchall()

    return render_template('books_available.html', books=available_books)

@app.route('/overdue', methods=['GET', 'POST'])
@login_required
def overdue():
    conn = connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                borrowed.*,
                students.*,
                books.*
            FROM
                borrowed
            INNER JOIN
                students ON borrowed.student_id = students.student_id
            INNER JOIN
                books ON borrowed.book_id = books.book_id
            WHERE
                borrowed.status_id = 1;
            """)
        overdue_books = cur.fetchall()
    conn.close()

    overdue = []
    print("Overdue Books: ", overdue_books)
    print("overdue: ", overdue)
    total_overdue_days = 0
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    print("Current Date: ", current_date)

    for od in overdue_books:
        book_title = od[21]
        borrower = od[8] + " " + od[7]
        borrowed_date = od[3]

        expected_return_date = od[4]
        expected_return_datetime = datetime.combine(expected_return_date, datetime.min.time())
        overdue_days = (current_date - expected_return_datetime).days

        print(overdue_days)

        if overdue_days > 0:
            total_overdue_days += overdue_days
            overdue.append([book_title, borrower, borrowed_date, expected_return_date, overdue_days, total_overdue_days])

    return render_template('overdue.html', overdue=overdue)

@app.route('/books_delete_data/<int:book_id>', methods=['GET', 'POST'])
@login_required
def book_delete_data(book_id):
    conn = connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM books WHERE book_id = %s", [book_id])
        conn.commit()
    conn.close()
    return redirect(url_for('books_available'))

@app.route('/books_update_data/<int:book_id>', methods=['GET', 'POST'])
@login_required
def book_update_data(book_id):
    print("Book ID: ", book_id)
    conn = connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM books WHERE book_id = %s", [book_id])
        data = cur.fetchone()
    conn.close()

    print("Data: ", data[7])

    file_path = f"static/img/qr_code/books/{data[7]}"
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Removed file: {file_path}")
        else:
            print(f"File {file_path} does not exist.")
    except Exception as e:
        print(f"Error removing file {file_path}: {e}")

    if request.method == "POST":
        accession_number = request.form['editAccNumber']
        call_number = request.form['editCallNumber']
        book_title = request.form['editTitle']
        author = request.form['editAuthor']
        genre = request.form['editGenre']
        publication_year = request.form['editDatePublished']

        # Handle file upload
        if 'editBookImg' in request.files:
            file = request.files['editBookImg']
            if file.filename != '':
                # Save the uploaded file
                filename = secure_filename(file.filename)
                file_path = os.path.join('static/img/book_img', filename)
                file.save(file_path)
            else:
                # If no file is uploaded, keep the existing image
                file_path = data[8]  # Assuming data[8] contains the existing image path
        else:
            file_path = data[8]  # Fallback to existing image path

        # Generate QR code
        qr_code_path = generate_book_qr_code(accession_number, book_title, author, genre, publication_year)

        # Update the database
        conn = connection()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE books SET accession_number=%s,call_number=%s, book_title=%s, author=%s, genre=%s, publication_year=%s, qr_code=%s, src_img=%s WHERE book_id=%s",
                (accession_number,call_number, book_title, author, genre, publication_year, qr_code_path, file_path, book_id)
            )
            conn.commit()
        conn.close()
        return redirect(url_for('books_available'))
    return render_template('book_update_data.html', data=data)


@app.route('/student_delete_data/<int:student_id>', methods=['GET', 'POST'])
@login_required
def student_delete_data(student_id):
    conn = connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM students WHERE student_id = %s", [student_id])
        conn.commit()
    conn.close()
    return redirect(url_for('students'))



@app.route('/most_active', methods=['GET', 'POST'])
@login_required
def most_active():
    conn = connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                s.*,
                COUNT(b.borrow_id) AS num_borrowed_books
            FROM
                students s
            LEFT JOIN
                borrowed b ON s.student_id = b.student_id
            GROUP BY
                s.student_id, s.student_fname
            ORDER BY
                num_borrowed_books DESC
            LIMIT 9999;
            """)
        most_active_student = cur.fetchall()
        print("Most Active Student: ", most_active_student)
    conn.close()
    return render_template('most_active.html', most_active_student = most_active_student)

#Adding Students
@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    conn = None  # Initialize conn to None
    if request.method == 'POST':
        print("Form data received:", request.form)  # Debugging
        print("Files received:", request.files)  # Debugging

        try:
            # Extract form data
            student_fname = request.form.get('fname')
            student_lname = request.form.get('lname')
            student_birthdate = request.form.get('birthdate')
            student_phone = request.form.get('phone')
            student_email = request.form.get('email')
            student_usn = request.form.get('usn')
            student_course = request.form.get('course')
            student_year = request.form.get('year')

            # Validate required fields
            if not all([student_fname, student_lname, student_birthdate, student_phone, student_email, student_usn, student_course, student_year]):
                flash("All fields are required", "error")
                print("Validation failed: All fields are required")  # Debugging
                return redirect(url_for('students'))

            # Validate phone number (ensure exactly 10 digits and no special characters)
            student_phone = student_phone.strip()  # Remove leading/trailing spaces
            if not student_phone.isdigit() or len(student_phone) != 10:
                flash("Invalid Phone Number. Must be 10 digits.", "error")
                print("Validation failed: Invalid phone number")  # Debugging
                return redirect(url_for('students'))

            # Check if the email domain is allowed
            if not is_allowed_domain(student_email):
                flash("Email domain not allowed", "error")
                print("Validation failed: Email domain not allowed")  # Debugging
                return redirect(url_for('students'))

            # Ensure a file was uploaded
            if 'student_picture' not in request.files or request.files['student_picture'].filename == '':
                flash("No image file uploaded", "error")
                print("Validation failed: No image file uploaded")  # Debugging
                return redirect(url_for('students'))

            profile_img = request.files['student_picture']

            # Validate file type
            if not allowed_file(profile_img.filename):
                flash("Invalid file type. Allowed types: png, jpg, jpeg, gif", "error")
                print("Validation failed: Invalid file type")  # Debugging
                return redirect(url_for('students'))

            # Generate unique filename for the image
            random_string = str(uuid.uuid4().hex)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f"{timestamp}_{random_string}.png"

            # Save profile image
            img_filename = f"{timestamp}_{random_string}.png"
            img_upload_folder = "static/img/students_image/"
            if not os.path.exists(img_upload_folder):
                os.makedirs(img_upload_folder)
            img_relative_path = os.path.join("img", "students_image", img_filename).replace("\\", "/")  # Ensure forward slashes
            img_absolute_path = os.path.join(img_upload_folder, img_filename)  # Absolute path
            profile_img.save(img_absolute_path)
            print("✅ Image saved at:", img_absolute_path)  # Debugging
            print("✅ Image relative path:", img_relative_path)  # Debugging

            # Generate QR code
            qr_data = f"""
                    Name: {student_fname} {student_lname}
                    Birthdate: {student_birthdate}
                    Phone: {student_phone}
                    Email: {student_email}
                    USN: {student_usn}
                    Program: {student_course}
                    Year: {student_year}
                    """
            qr_filename = f"qr_{timestamp}_{random_string}.png"
            qr_code_folder = "static/img/qr_code/students"
            if not os.path.exists(qr_code_folder):
                os.makedirs(qr_code_folder)

            # Save QR code to the correct location
            
            qr_code_relative_path = os.path.join("img/qr_code/students", qr_filename)  # Relative path
            qr_code_absolute_path = os.path.join(qr_code_folder, qr_filename)  # Absolute path
            qr = qrcode.make(qr_data)
            qr.save(qr_code_absolute_path)

            print("✅ QR Code saved at:", qr_code_absolute_path)  # Debugging
            print("✅ QR Code relative path:", qr_code_relative_path)  # Debugging

            # Check if the student already exists in the database
            conn = connection()
            if not conn:
                flash("Database connection error", "error")
                print("Database connection failed")  # Debugging
                return redirect(url_for('students'))

            with conn.cursor() as cur:
                cur.execute("SELECT * FROM students WHERE student_usn = %s", (student_usn,))
                existing_student = cur.fetchone()

                if existing_student:
                    flash("Student already exists in the database. Please check the USN.", "error")
                    print("Validation failed: Student already exists")  # Debugging
                    return redirect(url_for('students'))

                # Insert the new student into the database
                query = """
                    INSERT INTO students 
                    (student_fname, student_lname, student_birthdate, student_phone, student_email, student_usn, program, year_lvl, student_picture, qr_code, user_id) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    student_fname, student_lname, student_birthdate, student_phone, student_email, 
                    student_usn, student_course, student_year, img_relative_path, qr_code_relative_path, session['user_id']
                )

                print("Executing query:", query)  # Debugging
                print("With parameters:", params)  # Debugging
                cur.execute(query, params)
                conn.commit()

            flash("✅ Student added successfully", "success")
            print("Redirecting to /students")  # Debugging
            return redirect(url_for('students'))

        except Exception as e:
            print(f"❌ An error occurred: {str(e)}")  # Debugging
            flash(f"An error occurred: {str(e)}", "error")
            return redirect(url_for('students'))

        finally:
            if conn:  # Ensure conn is defined before closing
                conn.close()
    else:
        return redirect(url_for('students'))


import os
from werkzeug.utils import secure_filename

from flask import request, jsonify
import os
from werkzeug.utils import secure_filename


import os
from werkzeug.utils import secure_filename
from flask import request, jsonify

@app.route('/update_student', methods=['POST'])
def update_student():
    try:
        # Debugging: Log the incoming request data
        print("Form Data:", request.form)
        print("Files:", request.files)

        # Retrieve data from the form
        student_id = request.form.get('student_id')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        birth_date = request.form.get('birth_date')
        phone = request.form.get('contact_number')
        email = request.form.get('email')
        usn = request.form.get('usn')
        program = request.form.get('program')
        year = request.form.get('year')
        student_picture = request.files.get('student_picture')  # Handle file upload
        existing_image_path = request.form.get('existing_image_path')  # Existing image path

        # Input validation
        if not all([student_id, first_name, last_name, birth_date, phone, email, usn, program, year]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Debugging: Log the received data
        print(f"Updating student with ID {student_id} with the following data:")
        print(f"First Name: {first_name}")
        print(f"Last Name: {last_name}")
        print(f"Birth Date: {birth_date}")
        print(f"Contact Number: {phone}")
        print(f"Email: {email}")
        print(f"USN: {usn}")
        print(f"Program: {program}")
        print(f"Year: {year}")
        print(f"Student Image: {student_picture.filename if student_picture else 'No image uploaded'}")

        # Handle file upload
        img_path = existing_image_path  # Default to existing image path
        if student_picture:
            # Validate file extension
            allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
            filename = secure_filename(student_picture.filename)
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
            if file_ext not in allowed_extensions:
                return jsonify({'success': False, 'error': 'Invalid file type. Allowed types: png, jpg, jpeg, gif'}), 400

            # Generate unique filename for the image
            random_string = str(uuid.uuid4().hex)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            img_filename = f"{timestamp}_{random_string}.png"

            # Save profile image
            img_upload_folder = "static/img/students_image/"
            if not os.path.exists(img_upload_folder):
                os.makedirs(img_upload_folder)
            img_relative_path = os.path.join("img", "students_image", img_filename).replace("\\", "/")  # Ensure forward slashes
            img_absolute_path = os.path.join(img_upload_folder, img_filename)  # Absolute path
            student_picture.save(img_absolute_path)
            print("✅ Image saved at:", img_absolute_path)  # Debugging
            print("✅ Image relative path:", img_relative_path)  # Debugging

            # Use the relative path for the database
            img_path = img_relative_path

        # Update the database
        conn = connection()
        if not conn:
            print("Failed to connect to the database.")
            return jsonify({'success': False, 'error': 'Database connection failed'}), 500

        try:
            with conn.cursor() as cur:
                # Update the student record
                cur.execute(
                    """
                    UPDATE students 
                    SET 
                        student_fname = %s, 
                        student_lname = %s, 
                        student_birthdate = %s, 
                        student_phone = %s, 
                        student_email = %s, 
                        student_usn = %s, 
                        program = %s, 
                        year_lvl = %s, 
                        student_picture = %s 
                    WHERE 
                        student_id = %s
                    """,
                    (first_name, last_name, birth_date, phone, email, usn, program, year, img_path, student_id)
                )
                conn.commit()
            print("Database update successful!")
            return jsonify({'success': True}), 200
        except Exception as e:
            print(f"Database error: {e}")
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            if conn:
                conn.close()
    except Exception as e:
        print(f"Error updating student: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
@app.route('/add_books', methods=['GET', 'POST'])
@login_required
def add_books():
    if request.method == 'POST':
        accession_number = request.form['acc_number']
        call_number = request.form['call_number']
        book_title = request.form['title']
        book_author = request.form['author']
        book_genre = request.form['genre']
        date_published = request.form['date_published']
        publication_year = date_published.split('-')[0]
        profile_img = request.files['book_image']

        random_string = str(uuid.uuid4().hex)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        filename = f"{timestamp}_{random_string}.png"
        img_path = os.path.join(f"static/img/book_img/{filename}")
        profile_img.save(img_path)

        file_path = generate_book_qr_code(accession_number, book_title, book_author, book_genre, date_published)

        print("Accession Number: ", accession_number)
        conn = connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM books")
            book_data = cur.fetchall()
        conn.close()

        for book in book_data:
            print("Book Data: ", book[1])
            if accession_number in book[1]:
                return "Book already exists in the database. Please check the accession number."

        conn = connection()
        with conn.cursor() as cur:
            # cur.execute("INSERT INTO books VALUES(NULL, %s, %s, %s, %s, %s)", (book_title, book_author, book_genre, date_published, file_path))
            cur.execute("INSERT INTO books (accession_number,call_number, book_title, author, genre, publication_year, status_id, qr_code,src_img) VALUES (%s,%s, %s, %s, %s, %s, %s, %s, %s)", (accession_number,call_number, book_title, book_author, book_genre, publication_year, 1, file_path,img_path))
            conn.commit()
        conn.close()

        flash("Book added successfully", "success")
        return redirect(url_for('books_available'))

#-------------------------------------------LOGIN----------------------------------->>>
@app.route("/login", methods=["POST"])
def login():
    return render_template("login.html")

@app.route("/login_process", methods=["POST"])
def login_process():
    email = request.form['email']
    password = request.form['password']

    conn = connection()
    if conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email,password))
        user = cur.fetchone()
        print(user)

        if user:
                session['logged'] = True
                session['user_id'] = user[0]
                session['email'] = user[1]
                session['fname'] = user[2]
                return redirect(url_for('dashboard'))
        else:
            return "Invalid email or password"
    else:
        return "Error: Could not connect to the database."
    return render_template('index.html')


#-------------------------------------------REGISTRATION----------------------------------->>>

def is_allowed_domain(email):
    allowed_domains = ["@aclcbutuan.edu.ph"]  # You can fetch this from your database as well
    for domain in allowed_domains:
        if email.endswith(domain):
            return True
    return False

# Register route
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        email = request.form['email']
        fname = request.form['fname']
        mname = request.form['mname']
        lname = request.form['lname']
        password = request.form['password']
        contact = request.form['contact']
        datebirth = request.form['dateBirth']
        address = request.form['address']
        print(contact)

        if len(contact) != 10:
            flash("Invalid Phone Number", "error")
            return redirect(url_for('register'))

        else:
            pass

            # Check if the email domain is allowed
            if not is_allowed_domain(email):
                flash("Email domain not allowed", "error")  # Flash error message
                return render_template('signup.html')

            # If the email domain is allowed, proceed with registration
            conn = connection()  # Assuming you have a function to establish DB connection
            with conn.cursor() as cur:
                cur.execute("INSERT INTO users VALUES(NULL,%s, %s, %s, %s, %s,%s, %s, %s)", (email, fname, mname, lname, contact, datebirth, address, password))
                conn.commit()
            conn.close()

            flash("Account created successfully", "success")  # Flash success message
            return render_template('signup.html')

    return render_template('signup.html')

# Route for fetching and editing user profile
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required  # Ensure the user is logged in
def edit_profile():
    # Get the current user's ID from the session
    current_user_id = session.get('user_id')
    if not current_user_id:
        flash("User not logged in.", "error")
        return redirect(url_for('index'))

    # Establish database connection
    conn = connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        # Get updated user information from the form
        fname = request.form.get('fname')
        mname = request.form.get('mname')
        lname = request.form.get('lname')
        email = request.form.get('email')
        contact_no = request.form.get('contactNo')
        date_of_birth = request.form.get('dateOfBirth')
        address = request.form.get('address')

        try:
            # Update user's profile in the database
            cursor.execute("""
                UPDATE users 
                SET fname = %s, mname = %s, lname = %s, email = %s, contact_no = %s, date_of_birth = %s, address = %s 
                WHERE user_id = %s
            """, (fname, mname, lname, email, contact_no, date_of_birth, address, current_user_id))
            conn.commit()

            flash("Profile updated successfully!", "success")
            return redirect(url_for('profile'))

        except MySQLdb.Error as e:
            # Handle database errors
            conn.rollback()
            flash(f"Error updating profile: {str(e)}", "error")
            return redirect(url_for('edit_profile'))

        finally:
            # Close database connection
            cursor.close()
            conn.close()

    else:
        # Fetch current user's information from the database
        try:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user_id,))
            user = cursor.fetchone()

            if not user:
                flash("User not found.", "error")
                return redirect(url_for('index'))

            # Render the profile edit form with user's information
            return render_template('edit_profile.html', user=user)

        except MySQLdb.Error as e:
            flash(f"Error fetching user data: {str(e)}", "error")
            return redirect(url_for('index'))

        finally:
            # Close database connection
            cursor.close()
            conn.close()
    
    
@app.route('/update_penalty', methods=['POST'])
def update_penalty():
    data = request.json
    book_id = data['id']
    days_overdue = data['days_overdue']
    penalty_rate_per_day = 5

    conn = connection()
    try:
        with conn.cursor() as cur:
            # Retrieve borrow_id from borrowed table
            cur.execute("SELECT borrow_id FROM borrowed WHERE book_id = %s AND status_id = 2", (book_id,))
            borrow_id = cur.fetchone()[0]

            # Calculate penalty amount based on days overdue
            penalty = days_overdue * penalty_rate_per_day

            # Update penalty in borrowed table
            cur.execute("UPDATE borrowed SET late_fee = %s WHERE borrow_id = %s", (penalty, borrow_id))
            conn.commit()

            return jsonify({'success': True, 'message': f'Penalty updated successfully for book_id {book_id}'})

    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)})

    finally:
        conn.close()



@app.route("/logout")
@login_required
def logout():
    session.pop('logged', None)
    session.pop('user_id', None)
    session.pop('email', None)
    session.pop('fname', None)
    # flash("Logged out successfuly.", "success")
    return redirect(url_for('index'))

from datetime import datetime

from datetime import datetime

@app.route("/digital_lib_card/<int:student_id>", methods=['GET', 'POST'])
@login_required
def digital_lib_card(student_id):

    print("Student ID: ", student_id)
    conn = connection()

    with conn.cursor() as cur:
        # Fetch borrowed books for the student
        cur.execute("""
            SELECT
                borrowed.*,
                students.*,
                books.*
            FROM
                borrowed
            INNER JOIN
                students ON borrowed.student_id = students.student_id
            INNER JOIN
                books ON borrowed.book_id = books.book_id
            WHERE
                borrowed.student_id = %s;
            """, (student_id,))
        borrowed = cur.fetchall()

        # Fetch returned books for the student
        cur.execute("""
            SELECT r.return_id, r.return_date, r.late_fee,
                b.borrow_date, b.return_date,
                s.student_fname,s.student_lname, s.student_email,
                bk.book_title, bk.author
            FROM returned r
            JOIN borrowed b ON r.borrow_id = b.borrow_id
            JOIN students s ON b.student_id = s.student_id
            JOIN books bk ON b.book_id = bk.book_id
            WHERE b.student_id = %s;
            """, (student_id,))
        returned_books = cur.fetchall()

        # Fetch all borrowed books for the student
        cur.execute("""
            SELECT
                borrowed.*,
                students.*,
                books.*
            FROM
                borrowed
            INNER JOIN
                students ON borrowed.student_id = students.student_id
            INNER JOIN
                books ON borrowed.book_id = books.book_id
            WHERE
                borrowed.student_id = %s;
            """, (student_id,))
        all_borrowed_books = cur.fetchall()

        # Fetch student data based on student ID
        cur.execute("""
            SELECT * FROM students WHERE student_id = %s;
            """, (student_id,))
        student_data = cur.fetchone()

        overdue_books = []
        total_overdue_days = 0
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        print("Overdue: ", all_borrowed_books)
        for od in all_borrowed_books:
            book_title = od[21]
            borrower = od[8] + " " + od[7]

            borrowed_date = od[3]
            expected_return_date = od[4]
            expected_return_datetime = datetime.combine(expected_return_date, datetime.min.time())
            overdue_days = (current_date - expected_return_datetime).days
            print("Overdue Days: ", overdue_days)
            if overdue_days > 0:
                total_overdue_days += overdue_days
                overdue_books.append([book_title, borrower, borrowed_date, expected_return_date, overdue_days, total_overdue_days])
    conn.close()

    return render_template('digital_lib_card.html', overdue_books=overdue_books, returned_books=returned_books, borrowed=borrowed, student_data=student_data)


if __name__ == "__main__":
    socketio.run(app,debug=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
    