from flask import Flask,render_template,request,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash ,check_password_hash
from flask_login import login_user , logout_user ,login_manager ,LoginManager
from flask_login import login_required , current_user
from sqlalchemy import text
from flask_mail import Mail , Message
import json
import os
from functools import wraps
from flask import abort
import re
from flask import session



# Load configuration from config.json
with open('config.json', 'r') as c:
    params = json.load(c)['params']

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'selvaraanni'

# Configure Flask-Mail using environment variables
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)

# Initialize Flask-Mail
mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Initialize SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/hms?charset=utf8mb4'
db = SQLAlchemy(app)

# Define database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(1000))
    is_admin = db.Column(db.Boolean, default=False)

class Patients(db.Model):
    pid = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    email = db.Column(db.String(50), unique=True)
    gender = db.Column(db.String(50))
    appointmentDate = db.Column(db.String(50))
    appointmentTime = db.Column(db.String(50))
    slot = db.Column(db.String(50))
    disease = db.Column(db.String(50))
    dept = db.Column(db.String(50))
    doctorname = db.Column(db.String(50))
    phonenumber = db.Column(db.String(50))

class Doctors(db.Model):
    did = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(50),unique = True)
    dept = db.Column(db.String(100))
    doctorname = db.Column(db.String(50))

class Trigr(db.Model):
    tid = db.Column(db.Integer, primary_key=True)
    pid = db.Column(db.Integer)
    name=db.Column(db.String(100))
    email = db.Column(db.String(50),unique = True)
    action = db.Column(db.String(50))
    timestamp=db.Column(db.String(50))
    
    


def is_doctor_email(email):
    # Define regex pattern for doctor emails
    pattern = r"^[a-zA-Z0-9._%+-]+@doctor+.in"
    # Use re.match to validate the email against the pattern
    return re.match(pattern, email) is not None

# Routes
@app.route('/')
def home():
    return render_template("index.html")



@app.route('/patients', methods=["POST", "GET"])
@login_required
def patients():

    doct = Doctors.query.all()
    
    if request.method == "POST":
        # Extract form data
        name = request.form.get('name')
        email = request.form.get('email')
        gender = request.form.get('gender')
        appointmentDate = request.form.get('appointmentDate')
        appointmentTime = request.form.get('appointmentTime')
        slot = request.form.get('slot')
        disease = request.form.get('disease')
        dept = request.form.get('department')  # Extract department information
        doctorname = request.form.get('doctorname')
        phonenumber = request.form.get('phonenumber')

        # Create a new patient entry
        new_patient = Patients(
            name=name,
            email=email,
            gender=gender,
            appointmentDate=appointmentDate,
            appointmentTime=appointmentTime,
            slot=slot,
            disease=disease,
            dept=dept,
            doctorname=doctorname,
            phonenumber=phonenumber
        )
        db.session.add(new_patient)
        db.session.commit()

        # Send confirmation email
        try:
            msg = Message('HOSPITAL MANAGEMENT SYSTEM', sender=params['gmail-user'], recipients=[email])
            msg.body = 'Your booking is confirmed! Thanks for choosing us'
            mail.send(msg)
        except Exception as e:
            flash(f"Error sending email: {str(e)}", "danger")

        flash("Booking Confirmed", "info")
        return redirect(url_for("patients"))

    return render_template("patients.html", doct=doct)


@app.route('/doctors', methods=["POST", "GET"])
@login_required
def doctors():
    if request.method == "POST":
        email = request.form.get('email')
        dept = request.form.get('department')  # Correct the name to match the form field
        doctorname = request.form.get('doctorname')

        # Check if the provided email is a valid doctor email
        if not is_doctor_email(email):
            flash("Please provide a valid doctor email address.", "danger")
            return render_template("doctors.html")

        new_doctors = Doctors(email=email, dept=dept, doctorname=doctorname)
        db.session.add(new_doctors)
        db.session.commit()
        flash("Booking information is stored", "info")
        return redirect(url_for('doctors'))

    # Render the doctors.html page for GET requests
    return render_template("doctors.html")


@app.route('/bookings')
@login_required
def bookings():
    em = current_user.email
    try:
        query_result = db.session.execute(text(f"SELECT * FROM patients WHERE email=:em"), {'em': em})
        patients = query_result.fetchall()
        return render_template('bookings.html', patients=patients)
    except Exception as e:
        print(f"Error fetching data: {str(e)}")
        return render_template('bookings.html', patients=[])

@app.route("/edit/<string:pid>" , methods = ["POST" , "GET"])
@login_required
def edit(pid):
    posts = Patients.query.filter_by(pid=pid).first()
    if request.method == "POST":
        name = request.form.get('name')
        email = request.form.get('email')
        gender = request.form.get('gender')
        appointmentDate = request.form.get('appointmentDate')
        appointmentTime = request.form.get('appointmentTime')
        slot = request.form.get('slot')
        disease = request.form.get('disease')
        doctorname = request.form.get('doctorname') 
        phonenumber = request.form.get('phonenumber')

        # Use placeholders in the query to prevent SQL injection
        query = text("UPDATE patients SET name=:name, email=:email, gender=:gender, "
        "appointmentDate=:appointmentDate, appointmentTime=:appointmentTime, "
        "slot=:slot, disease=:disease, doctorname=:doctorname, phonenumber=:phonenumber "
        "WHERE pid=:pid")

        try:
            db.session.execute(query, {
                'name': name,
                'email': email,
                'gender': gender,
                'appointmentDate': appointmentDate,
                'appointmentTime': appointmentTime,
                'slot': slot,
                'disease': disease,
                'doctorname': doctorname,
                'phonenumber': phonenumber,
                'pid': pid
            })
            db.session.commit()
            flash("Slot is updated", "success")
            return redirect('/bookings')
        except Exception as e:
            flash(f"Error updating slot: {str(e)}", "danger")

    return render_template('edit.html', posts=posts)

@app.route("/delete/<string:pid>" , methods = ["POST" , "GET"])
@login_required
def delete(pid):
    try:
        db.session.execute(text("DELETE FROM patients WHERE pid = :pid"), {'pid': pid})
        db.session.commit()
        flash("Slot deleted successfully", "danger")
    except Exception as e:
        flash(f"Error deleting slot: {str(e)}", "danger")
    return redirect('/bookings')



@app.route('/signup', methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("User with this email already exists.", "warning")
            return render_template('/signup.html')

        # Check if the email is admin's email
        if email == 'admin@doctor.in':
            new_user = User(username=username, email=email, password=generate_password_hash(password), is_admin=True)
        else:
            new_user = User(username=username, email=email, password=generate_password_hash(password), is_admin=False)

        db.session.add(new_user)
        db.session.commit()
        flash("Signup success. Please login.")
        return render_template('/login.html')

    return render_template('signup.html')



@app.route('/login', methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        # Print out the email and password received for debugging
        print(f"Received email: {email}")
        print(f"Received password: {password}")

        # Check if the provided credentials match those of the admin user
        admin_user = User.query.filter_by(email='admin@doctor.in').first()
        if email == 'admin@doctor.in' and admin_user and check_password_hash(admin_user.password, password):
            # Redirect to admin dashboard if credentials match admin user
            login_user(admin_user)
            flash("Login success", "primary")
            return redirect(url_for('admin_dashboard'))

        # For other users, check if they exist in the database
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login success", "primary")
            # Redirect the user to the page they were trying to access
            next_page = request.args.get('next')
            return redirect(next_page or url_for('patients'))  # Redirect to patients page if next_page is None
        else:
            flash("Invalid credentials", "danger")
            return redirect(url_for('login'))

    return render_template("login.html")



@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.is_admin:
        doctors = Doctors.query.all()
        patients = Patients.query.all()  # Fetch patients' data
        triggers = Trigr.query.all()
        return render_template("admin_dashboard.html", doctors=doctors, patients=patients)
    else:
        flash("You are not authorized to access this page.", "danger")
        return redirect(url_for("login"))



@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logout successful","primary")
    return redirect(url_for('login'))


    

@app.route('/search' , methods=["POST","GET"])
@login_required
def search():
    try:
        if request.method == "POST":
            query = request.form.get('search')
            print("Query:", query)  # Print the query to debug

            dept = Doctors.query.filter_by(dept=query).all()
            if dept:  
                flash("Department is available", "info")
            else:
                flash("Department is not available", "danger")
    except Exception as e:
        flash(f"Error occurred: {str(e)}", "danger")
        

    
    return render_template("index.html")




@app.route('/details')
@login_required
def details():
    
    posts = Trigr.query.all()
    return render_template("triggers.html", posts=posts)

if __name__ == "__main__":
    app.run(debug=True)
    