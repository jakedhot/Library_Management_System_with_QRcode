import sqlite3
import pandas as pd

# Connect to the SQLite database
conn = sqlite3.connect('library_database.db')

# Query the database to fetch library card data
query = "SELECT Name, CardNumber, IssueDate, ExpiryDate FROM library_cards;"
library_cards_df = pd.read_sql(query, conn)

# Close the database connection
conn.close()

# Export the dataframe to an Excel file with proper layout for library cards
with pd.ExcelWriter('library_cards.xlsx', engine='xlsxwriter') as writer:
    workbook = writer.book
    worksheet = workbook.add_worksheet()

    # Define formats for header and data
    header_format = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
    data_format = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1})

    # Write headers
    headers = ['Name', 'Library Card Number', 'Issue Date', 'Expiration Date']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    # Write data
    for row, (name, card_number, issue_date, expiry_date) in enumerate(library_cards_df.itertuples(index=False), start=1):
        worksheet.write(row, 0, name, data_format)
        worksheet.write(row, 1, card_number, data_format)
        worksheet.write(row, 2, issue_date, data_format)
        worksheet.write(row, 3, expiry_date, data_format)

    # Set column widths
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 25)
    worksheet.set_column('C:D', 15)
