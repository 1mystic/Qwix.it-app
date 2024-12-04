from . import db
from datetime import datetime,time
from pytz import timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from sqlalchemy import or_
from . import app

IST = timezone('Asia/Kolkata')
# models db
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    pincode = db.Column(db.Integer, nullable=True)
    phone = db.Column(db.Integer, nullable=False, default=1234567890)
    role = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(20), nullable=False, default='normal')
    is_approved = db.Column(db.Boolean, default=True)
    is_blocked = db.Column(db.Boolean, default=False)
    saved_packs = db.Column(db.String(20), nullable=True)

class Service(db.Model):
    __tablename__ = 'service'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500))
    category = db.Column(db.String(50), nullable=False) #emergency, platinum, normal

class Professional(db.Model):
    __tablename__ = 'professional'
    id = db.Column(db.Integer, primary_key=True)
    p_name = db.Column(db.String(150), nullable=False)
    p_email = db.Column(db.String(150), nullable=False)
    p_phone = db.Column(db.Integer, nullable=False)
    paddress = db.Column(db.String(300), nullable=False)
    ppassword = db.Column(db.String(150), nullable=False)
    p_pincode = db.Column(db.Integer, nullable=False)
    document_proof = db.Column(db.String(550), nullable=False) 
    experience_years = db.Column(db.String, nullable=False)
    rating = db.Column(db.Float, nullable=False, default=0.0)
    base_price = db.Column(db.Float, nullable=False, default=0.0)
    is_approved = db.Column(db.Boolean, default=False)
    is_blocked = db.Column(db.Boolean, default=True)    
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
   
    #relationship 
    user = db.relationship('User', backref='professional_profile')
    service = db.relationship('Service', backref=db.backref('professionals', lazy='dynamic'))

class ServicePackage(db.Model):
    __tablename__ = 'service_package'
    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    duration = db.Column(db.String, nullable=False, default='00:20:00')
    is_flagged = db.Column(db.Boolean, default=False)

    #relationship 
    professional = db.relationship('Professional', backref='service_packages')
    service = db.relationship('Service', backref='service_packages')

class ServiceRequest(db.Model):
    __tablename__ = 'service_request'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('service_package.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professional.id'), nullable=True)
    date_of_request = db.Column(db.DateTime, nullable=False, default=datetime.now(IST))
    date_of_completion = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='requested') #requested, accepted, completed, closed
    remarks = db.Column(db.String(500))

    # relationship
    customer = db.relationship('User', foreign_keys=[customer_id], backref=db.backref('service_requests', lazy='dynamic'))
    professional = db.relationship('Professional', foreign_keys=[professional_id], backref=db.backref('service_requests', lazy='dynamic'))
  
class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_request.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.String(500))
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now(IST))

    #relationship 
    service_request = db.relationship('ServiceRequest', backref='review')
    

# creating databases 
with app.app_context():
    
    db.create_all()
    try:
        #customer
        if not db.session.query(User).count():
            users = [
                User(username="admin", email="admin@admin", password=generate_password_hash("admin"),
                     address="Admin Address", role="admin", pincode=000000,phone=1234567890),
                User(username="Coshu", email="user@user", password=generate_password_hash("user"), 
                     address = "User Address", role="customer", type='normal', pincode=123456, phone=1234567890)
           ]
            db.session.bulk_save_objects(users)
            db.session.commit()
            
        #professional
        if not db.session.query(Professional).count():
            
            professionals = [
                Professional(
                    p_name="Anipro", 
                    p_email="pro@abc", 
                    p_phone=1234567890, 
                    paddress="prostreet procode lane protown", 
                    ppassword=generate_password_hash("pro"), 
                    p_pincode=123456, 
                    document_proof="Anipro.pdf", 
                    experience_years='3-5', 
                    rating=0, 
                    base_price=400.0, 
                    is_approved=True, 
                    is_blocked=False, 
                    service_id=1
                ),
                
                Professional(
                    p_name="Hikaru", 
                    p_email="test@pro", 
                    p_phone=1234567890, 
                    paddress="B Sector X town Indore", 
                    ppassword=generate_password_hash("testing"), 
                    p_pincode=123456, 
                    document_proof="Hikaru.pdf", 
                    experience_years='5-10', 
                    rating=0, 
                    base_price=500.0, 
                    is_approved=True, 
                    is_blocked=False, 
                    service_id=1
                ),
              
                Professional(
                    p_name="Bob Smith", 
                    p_email="bob@example.com", 
                    p_phone=1234567890, 
                    paddress="123 Main St, Anytown, USA", 
                    ppassword=generate_password_hash("password123"), 
                    p_pincode=123456, 
                    document_proof="Bob_Smith.pdf", 
                    experience_years='1-3', 
                    rating=0, 
                    base_price=200.0, 
                    is_approved=True, 
                    is_blocked=False,
                    service_id=3
                )
            ]
            db.session.bulk_save_objects(professionals)
            db.session.commit()
            
        #service
        if not db.session.query(Service).count():
            services = [
                Service(name="Plumbing", base_price=50.0, description="Normal Plumbing Service", category="normal"),
                Service(name="Cleaning", base_price=30.0, description="Normal Cleaning Service", category="normal"),
                Service(name="Cooking", base_price=30.0, description="Normal Cooking Service", category="normal"),
                Service(name="Repairs", base_price=30.0, description="Reapairing Service", category="normal"),          
                Service(name="Electrical", base_price=100.0, description="Normal Electrical Service", category="normal"),               
                Service(name="Laundry", base_price=50.0, description="Laundry Service", category="normal"),
                Service(name="Emergency Repairs", base_price=50.0, description="Emergency Repair Service", category="emergency") ,
                Service(name="Premium Cleaning", base_price=50.0, description="Premium Cleaning Service", category="platinum"),               
            ]
            db.session.bulk_save_objects(services)
            db.session.commit()
            
        #service_package
        if not db.session.query(ServicePackage).count():
            service_packages = [
                ServicePackage(id = 1 , professional_id=1, service_id=1, name="Faucet repair", price=100.0, description="Inspecting all faucets for leaks", duration='00:40:00'),
                ServicePackage(id = 2 , professional_id=1, service_id=1, name="Pressure check", price=80.0, description="Checking water pressure", duration='00:20:00'),
                ServicePackage(id = 3 , professional_id=1, service_id=1, name="Pipe fixtures", price=300.0, description="Tightening loose pipes and fixtures", duration='00:50:00'),
                ServicePackage(id = 4 , professional_id=2, service_id=1, name="Faucet repair", price=70.0, description="Inspecting all faucets for leaks", duration='00:40:00'),
                ServicePackage(id = 5 , professional_id=3, service_id=3, name="Breakfast Daily", price=600.0, description="Monthly breakfast for 2", duration='00:30:00'),
                 ]
            db.session.bulk_save_objects(service_packages)
            db.session.commit()

        #service_request
        if not db.session.query(ServiceRequest).count():
            service_requests = [
                ServiceRequest(customer_id=2, package_id=1, professional_id=1, date_of_request=datetime.strptime('2024-10-31 16:12:53', '%Y-%m-%d %H:%M:%S'), date_of_completion=datetime.strptime('2024-11-01 18:16:00', '%Y-%m-%d %H:%M:%S'), status='Closed', remarks='okay'),
                ServiceRequest(customer_id=2, package_id=3, professional_id=1, date_of_request=datetime.strptime('2024-10-31 16:12:53', '%Y-%m-%d %H:%M:%S'), date_of_completion=datetime.strptime('2024-11-01 18:16:00', '%Y-%m-%d %H:%M:%S'), status='Completed', remarks='well done')
                        
            ]
            db.session.bulk_save_objects(service_requests)
            db.session.commit()
        
        #review
        if not db.session.query(Review).count():
            reviews = [
                Review(service_request_id=1, rating=4, comment='Good service', date_created=datetime.strptime('2024-11-01 18:16:00', '%Y-%m-%d %H:%M:%S')),
                Review(service_request_id=2, rating=5, comment='Excellent service', date_created=datetime.strptime('2024-11-01 18:16:00', '%Y-%m-%d %H:%M:%S')),
            ]
            db.session.bulk_save_objects(reviews)
            db.session.commit()
       
        print("All data added successfully")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        db.session.rollback()
    finally:
        db.session.close()