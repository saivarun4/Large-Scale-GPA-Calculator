from flask import Flask, request, render_template, Response
import pandas as pd
from flask_sqlalchemy import SQLAlchemy
from model import db, FileData, Marks
import csv
from io import StringIO

app = Flask(__name__)

# Configure the database URI and suppress the deprecation warning
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///filedata.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            csv_file = request.files['file']
            if csv_file:
                # Specify the correct encoding (e.g., 'utf-8', 'iso-8859-1', 'cp1252')
                data = pd.read_csv(csv_file, encoding='utf-8')
                
                # Ensure that the first row is the header and skip it when storing data
                for _, row in data.iterrows():
                    # Create a FileData object and add it to the session
                    file_data = FileData(
                        name=row['name'], 
                        cae1=row['cae1'], 
                        cae2=row['cae2'], 
                        internals=row['internals'], 
                        externals=row['externals']
                    )
                    db.session.add(file_data)
                
                db.session.commit()
                return "File uploaded and data stored in the database."
            else:
                return "No file uploaded."
        except Exception as e:
            # Print the specific error message for debugging
            print(f"Error: {str(e)}")
            db.session.rollback()  # Rollback the transaction in case of an error
            return "Error occurred while processing the file."
    else:
        return render_template('upload.html')
    
def calculate_grade_points():
    # Retrieve data from the file_data table
    file_data_rows = FileData.query.all()

    # Calculate and store grade points for each row
    for row in file_data_rows:
        total_score = (row.cae1 + row.cae2) * 30 / (max(row.cae1, row.cae2) + row.internals + row.externals)
        total_score += row.internals + row.externals

        # Calculate grade points based on the total score
        if total_score > 90:
            grade_point = 10
        elif total_score > 80:
            grade_point = 9
        elif total_score > 70:
            grade_point = 8
        elif total_score > 60:
            grade_point = 7
        elif total_score > 50:
            grade_point = 6
        else:
            grade_point = 0

        # Store the calculated grade point in the marks table
        if grade_point is not None:
            marks_entry = Marks(name=row.name, grade_point=grade_point)
            db.session.add(marks_entry)

    # Commit the changes to the database
    db.session.commit()

@app.route('/calculate-grade-points', methods=['GET'])
def calculate_and_store_grade_points():
    calculate_grade_points()
    return "Grade points calculated and stored in the database."

# Define a new route for downloading marks data as CSV
@app.route('/download-marks', methods=['GET'])
def download_marks_data():
    # Retrieve data from the marks table
    marks_data = Marks.query.all()

    # Prepare CSV data
    csv_data = StringIO()
    csv_writer = csv.writer(csv_data)
    csv_writer.writerow(['id', 'name', 'grade_point'])  # CSV header
    for row in marks_data:
        csv_writer.writerow([row.id, row.name, row.grade_point])

    # Create response for CSV download
    response = Response(csv_data.getvalue(), content_type='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=marks_data.csv'

    return response


if __name__ == '__main__':
    app.run(debug=True)
