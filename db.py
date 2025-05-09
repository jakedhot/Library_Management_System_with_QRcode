from flask_mysqldb import MySQLdb
from dotenv import load_dotenv
import os

load_dotenv()

# MySQL Configuration
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PW = os.getenv('DB_PW')
DB_NAME = os.getenv('DB_NAME')

def create_db():
    # Connect to MySQL
    conn = MySQLdb.connect(host=DB_HOST, user=DB_USER, password=DB_PW)
    cursor = conn.cursor()

    # Create database
    cursor.execute("CREATE DATABASE IF NOT EXISTS {}".format(DB_NAME))
    conn.commit()

    # Switch to the database
    cursor.execute("USE {}".format(DB_NAME))

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(100) UNIQUE NOT NULL,
            fname VARCHAR(100) NOT NULL,
            mname VARCHAR(100),
            lname VARCHAR(100) NOT NULL,
            contact VARCHAR(100) NOT NULL,
            dateBirth VARCHAR(100) NOT NULL,
            address VARCHAR(100) NOT NULL,
            password VARCHAR(100) NOT NULL
        )
    """)
    conn.commit()

    # Create students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INT AUTO_INCREMENT PRIMARY KEY,
            student_fname VARCHAR(100) NOT NULL,
            student_lname VARCHAR(100) NOT NULL,
            student_birthdate DATE NOT NULL,
            student_phone VARCHAR(15) NOT NULL,
            student_email VARCHAR(100) NOT NULL,
            student_usn VARCHAR(100) NOT NULL,
            program VARCHAR(100) NOT NULL,
            year_lvl VARCHAR(100) NOT NULL,
            student_picture VARCHAR(255) NOT NULL,
            qr_code VARCHAR(255) NOT NULL,
            user_id INT,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # Create status table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS status (
            status_id INT AUTO_INCREMENT PRIMARY KEY,
            status_name VARCHAR(50) NOT NULL
        )
    """)
    conn.commit()

    # Insert default status values
    cursor.execute("SELECT COUNT(*) FROM status WHERE status_name IN ('Available', 'Not Available')")
    count = cursor.fetchone()[0]

    # If values don't exist, insert them
    if count == 0:
        cursor.execute("INSERT INTO status (status_name) VALUES ('Available'), ('Not Available'), ('Returned')")
        conn.commit()
        print("Status values inserted successfully.")
    else:
        print("Status values already exist in the table. Skipping insertion.")

    # Create books table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id INT AUTO_INCREMENT PRIMARY KEY,
            accession_number VARCHAR(100) NOT NULL,
            call_number VARCHAR(100) NOT NULL,
            book_title VARCHAR(255) NOT NULL,
            author VARCHAR(100) NOT NULL,
            genre VARCHAR(50) NOT NULL,
            publication_year YEAR NOT NULL,
            status_id INT,
            qr_code VARCHAR(255) NOT NULL,
            src_img VARCHAR(255),  -- Add this column
            FOREIGN KEY (status_id) REFERENCES status(status_id) ON DELETE CASCADE
        )
    """)
    conn.commit()


    # Create borrow table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS borrowed (
            borrow_id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            book_id INT,
            borrow_date DATE,
            return_date DATE,
            status_id INT,
            FOREIGN KEY (status_id) REFERENCES status(status_id) ON DELETE CASCADE,
            FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
            FOREIGN KEY (book_id) REFERENCES books(book_id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # Create return table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS returned (
            return_id INT AUTO_INCREMENT PRIMARY KEY,
            borrow_id INT,
            return_date DATE,
            late_fee DECIMAL(10, 2),
            FOREIGN KEY (borrow_id) REFERENCES borrowed(borrow_id) ON DELETE CASCADE
        )
    """)
    conn.commit()

    # Create allowed_domains table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS allowed_domains (
            id INT AUTO_INCREMENT PRIMARY KEY,
            domain VARCHAR(255) NOT NULL
        )
    """)
    conn.commit()

    # Insert allowed domains
    cursor.execute("SELECT COUNT(*) FROM allowed_domains WHERE domain = %s", ('@aclcbutuan.edu.ph',))
    count = cursor.fetchone()[0]
    if count == 0:
        cursor.execute("INSERT INTO allowed_domains (domain) VALUES (%s)", ('@aclcbutuan.edu.ph',))
        conn.commit()
        print("Allowed domain inserted successfully.")
    else:
        print("Allowed domain already exists in the table. Skipping insertion.")

    cursor.close()
    conn.close()

create_db()  # Call the function to create the database and tables
