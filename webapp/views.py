from flask import current_app

from flask import redirect, request, render_template, url_for, flash, session, get_flashed_messages
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime,time
from pytz import timezone
from sqlalchemy import func
from sqlalchemy import or_

import os 
from . import app, db
from .models import Professional, Service, ServicePackage, User,Review, ServiceRequest



ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
IST = timezone('Asia/Kolkata')
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#landing page
@app.route('/', methods=['GET'])
def home():
    logged_in = session.get('logged_in', False)
    userole = session.get('userole', None)
    return render_template('land.html', logged_in=logged_in, userole=userole)

# login routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('log.html')
    
    elif request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        
        if role == "professional":
            professional = Professional.query.filter_by(p_email=email).first()
            if professional and check_password_hash(professional.ppassword, password) and professional.is_approved:          
                
                    session['username'] = professional.p_name
                    session['logged_in'] = True
                    session['userole'] = "professional"
                    session['saved_packages'] = []
                    return redirect(url_for('pro_dash'))
            elif professional and check_password_hash(professional.ppassword, password) and professional.is_blocked : 
                    flash('Your account is blocked', 'error') 
                    return render_template('log.html')
            else :
                flash('Invalid credentials or your request was rejected', 'error')
                return render_template('log.html')
        else:
            user = User.query.filter_by(email=email, role=role).first()
            if user and (not user.is_blocked) and user.is_approved and check_password_hash(user.password, password):
                                
                if user:
                    session['username'] = user.username
                    session['logged_in'] = True
                    session['userole'] = role
                    if role == "customer":
                        return redirect(url_for('cust_dash'))
                    elif role == "admin":
                        return redirect(url_for('admin'))
            elif user and user.is_blocked :
                flash('Your account is blocked', 'error') 
                return render_template('log.html')
            else :
                flash('Invalid email or password', 'error')
                return render_template('log.html')
                              
        
        

    return render_template('log.html')

# logout route
@app.route('/logout')
def logout():
    session.clear()
    return render_template('land.html')


# register routes
@app.route('/register_cust', methods=['GET', 'POST'])
def register_cust():
    
    if request.method == 'GET':
        return render_template('register_cust.html')
    
    elif request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        pwd = request.form['password']
        password = generate_password_hash(pwd)
        address = request.form['address']
        pincode = request.form['pincode']
        role = request.form['role']
        
        existing_user = User.query.filter_by(email=email).first()
        existing_pro = Professional.query.filter_by(p_email=email).first()
        if existing_user or existing_pro:
            flash('Email already registered', 'error')
            return redirect(url_for('register_cust'))
        
        new_customer = User(username=username, email=email, password=password, address=address,pincode=pincode, role=role)
        db.session.add(new_customer)
        db.session.commit()
        
        
        flash('Registration successful', 'success')
        return redirect(url_for('login'))

# register professional
@app.route('/register_pro', methods=['GET', 'POST'])
def register_pro():
    if request.method == 'GET':
        
        ## data for the form 
        services_d = Service.query.all()
        
        services = []
        for s in services_d:
            services.append({
                'service_id': s.id,
                'service_name': s.name 
            })
      
        
        return render_template('register_pro.html', services=services)

    elif request.method == 'POST':
        p_name = request.form['p_name']
        p_email = request.form['p_email']
        p_phone = request.form['p_phone']
        p_address = request.form['p_address']
        password = request.form['p_password']
        p_password = generate_password_hash(password)
        p_pincode = request.form['p_pincode']
        base_price = request.form['p_base_price']
        experience = request.form['experience']
        
        file = request.files['document']
        if file :
            
            if app.config['MAX_CONTENT_LENGTH'] < file.content_length:
                flash('File size too large', 'error')
                return redirect(url_for('register_pro'))
            else:
                new_filename = secure_filename(f"{p_name}.pdf")
                upload_folder = os.path.join(current_app.static_folder, 'docs')
                os.makedirs(upload_folder, exist_ok=True)
                
                fileloc = os.path.join(upload_folder, new_filename)
                file.save(fileloc)
        else :
            flash('No file selected', 'error')
            return redirect(url_for('register_pro'))
        
            
        # Saving all data
        service_type = request.form['service_type']
        service = Service.query.filter_by(name=service_type).first()
        if not service:
            flash('Service type not found', 'error')
            return redirect(url_for('register_pro'))
        
        existing_user = User.query.filter_by(email=p_email).first()
        existing_pro = Professional.query.filter_by(p_email=p_email).first()
        if existing_user or existing_pro:
            flash('Email already registered', 'error')
            return redirect(url_for('register_pro'))
        
        new_pro = Professional(p_name=p_name, p_email=p_email, p_phone=p_phone, paddress=p_address,
                               ppassword=p_password, p_pincode=p_pincode,base_price=base_price,
                               document_proof = new_filename, experience_years=experience,
                              service_id=service.id)
        db.session.add(new_pro)
        db.session.commit()
        
        flash('Registration successful', 'success')
        return redirect(url_for('login'))
    
    
# customer routes  
  
  #customer dashboard
@app.route('/cust_dash', methods=['GET'])
def cust_dash():
    if 'username' not in session:
        return redirect(url_for('login'))
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
  
    if  session.get('logged_in') and session.get('userole') == 'customer':
        
        current_user = User.query.filter_by(username=session['username']).first()
        if current_user : 
            customer_type = current_user.type
        services_data = Service.query.filter(Service.category=='normal').all()
        
        services_available = []
        
        if services_data:
            for s in services_data:
                services_available.append({
                    'service_id': s.id,
                    'service_name': s.name
                })
            
        platinum_services = Service.query.filter(Service.category=='platinum').all()
        platinum_services_available = []
        
        if platinum_services:
            for s in platinum_services:
                platinum_services_available.append({
                    'service_id': s.id,
                    'service_name': s.name
                })
                
        emergency_services = Service.query.filter(Service.category=='emergency').all()
        emergency_services_available = []
        
        if emergency_services:
            for s in emergency_services:
                emergency_services_available.append({
                    'service_id': s.id,
                    'service_name': s.name
                })
            
        statuses = ['Requested', 'Accepted','Rejected']

        booked_requests = ServiceRequest.query.filter(ServiceRequest.customer_id == current_user.id,
                                                      ServiceRequest.status.in_(statuses)).all()

        booked_data = []
        
        if booked_requests:
            for request in booked_requests:
                service_cat = db.session.query(Service.name).join(ServicePackage, Service.id == ServicePackage.service_id).filter(ServicePackage.id == request.package_id).scalar()
                professional = Professional.query.get(request.professional_id).p_name
                phone = Professional.query.get(request.professional_id).p_phone
                experience = Professional.query.get(request.professional_id).experience_years
                package_name = db.session.query(ServicePackage.name).join(ServiceRequest).filter(ServiceRequest.id == request.id).scalar()
                booked_data.append({
                    'service_request_id': request.id,
                    'service_category': service_cat if service_cat else 'Unknown Category',
                    'service_name': package_name if package_name else 'Unknown Service',
                    'professional_name': professional if professional else 'Not Assigned',   
                    'date_time': request.date_of_completion,
                    'phone': phone if phone else 'Not Assigned',
                    'experience': experience if experience else 'Not Assigned',
                    'status': request.status,
                    'package_id': request.package_id
                })
            
        all_requests = ServiceRequest.query.filter_by(customer_id=current_user.id).all()
        service_history=[]
        
        if all_requests:
            for r in all_requests:
                professional = Professional.query.get(r.professional_id)
                if professional:
                    professional = professional.p_name
                phone = Professional.query.get(r.professional_id)
                if phone:
                    phone = phone.p_phone
                package_name = ServicePackage.query.get(r.package_id)
                if package_name:
                    package_name = package_name.name
                experience = Professional.query.get(r.professional_id)
                if experience:
                    experience = experience.experience_years
                service_cat = Service.query.join(ServicePackage, Service.id == ServicePackage.service_id).filter(ServicePackage.id == r.package_id).with_entities(Service.name).scalar()
                service_history.append({
                    'service_request_id': r.id,
                    'service_category': service_cat if service_cat else 'Unknown Category',
                    'service_name': package_name if package_name else 'Unknown Service',
                    'professional_name': professional if professional else 'Not Assigned',   
                    'booked_date': r.date_of_request,
                    'completion_date': r.date_of_completion,
                    'phone': phone if phone else 'Not Assigned',
                    'experience': experience if experience else 'Not Assigned',
                    'status': r.status,
                    'package_id': r.package_id
                })
        
        return render_template('cust_dash.html', username=session['username'],
                               usertype = customer_type,
                               services_available=services_available,
                               platinum_services_available=platinum_services_available,
                                 emergency_services_available=emergency_services_available,
                               booked_data=booked_data,
                               service_history=service_history)
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
    
# get platinum plan 
@app.route('/platinum', methods=['GET','POST'])
def platinum():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    if request.method == 'GET' and session.get('logged_in') and session.get('userole') == 'customer':
        
        cust = User.query.filter_by(username=session['username']).first() 
        cust_id = cust.id  
        type = cust.type
        if type == 'Platinum':
            flash('You are already a platinum customer', 'error')
            return redirect(url_for('cust_dash'), customer_name=session['username'])
        
        return render_template('platinum.html', customer_name=session['username'], customer_id = cust_id)
    
    if request.method == 'POST' :
        cust_id = request.form.get('customer_id')
        customer = User.query.get(cust_id)
        customer.type = 'Platinum'
        db.session.commit()
        flash('Platinum plan activated successfully', 'success')        
        return redirect(url_for('cust_dash'))
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
    
    
#save packages
@app.route('/save_package/<int:pkg_id>', methods=['GET'])
def save_package(pkg_id):
    if not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    if request.method == 'GET' and session.get('logged_in') and session.get('userole') == 'customer':
        
           
        s_id = ServicePackage.query.get(pkg_id)
        if s_id:
            s_id = s_id.service_id
        
        # already saved packs 
        cust = User.query.filter_by(username=session['username']).first()
        if cust:
            if cust.saved_packs:
                if str(pkg_id) in cust.saved_packs:
                    flash('Package already saved', 'error')
                    return redirect(url_for('packages', service_id=s_id))
                else : 
                    cust.saved_packs = cust.saved_packs + ',' + str(pkg_id)

            else:
                if not cust.saved_packs:
                    cust.saved_packs = str(pkg_id)
                
       
        db.session.commit()
        
        flash('Package saved successfully', 'success')
        return redirect(url_for('packages', service_id=s_id)) 
     
# unsave package 
@app.route('/unsave_package/<int:pkg_id>', methods=['GET'])
def unsave_package(pkg_id):
    if not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    if request.method == 'GET' and session.get('logged_in') and session.get('userole') == 'customer':
        
        # remove from db 
        current_user = User.query.filter_by(username=session['username']).first()
        if current_user:
            if current_user.saved_packs:
                current_user.saved_packs = current_user.saved_packs.replace(f',{pkg_id}', '').replace(f'{pkg_id},', '').replace(f'{pkg_id}', '')
            
            
        db.session.commit()     
        flash('Package removed successfully', 'success')
        return redirect(url_for('saved_packages'))

# page for saved packages
@app.route('/saved_packages', methods=['GET'])
def saved_packages():
    if not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    if request.method == 'GET' and session.get('logged_in') and session.get('userole') == 'customer':
        
        saved_packs = User.query.filter_by(username=session['username']).first()
        if saved_packs:
            saved_packs = saved_packs.saved_packs 
       
        packages = []
        
        if saved_packs :
            for p in saved_packs:
                package = ServicePackage.query.get(p)
                if package:
                    service_name = Service.query.get(package.service_id)
                    if service_name:
                        service_name = service_name.name
                    professional_name = Professional.query.get(package.professional_id)
                    if professional_name:
                        professional_name = professional_name.p_name
                    phone = Professional.query.get(package.professional_id)
                    if phone:
                        phone = phone.p_phone
                    experience_years = Professional.query.get(package.professional_id)
                    if experience_years:
                        experience_years = experience_years.experience_years
                        
                    service_type = Service.query.get(package.service_id)
                    if service_type:
                        service_type = service_type.category
                    if service_type == 'normal':
                        service_type = 'Regular Service'

                    avg_rating = Review.query.join(ServiceRequest, ServiceRequest.id == Review.service_request_id).filter(
                                ServiceRequest.package_id == package.id
                                    ).with_entities(func.avg(Review.rating).label('avg_rating')).scalar()
                
                    review_count = Review.query.join(ServiceRequest).filter(ServiceRequest.package_id == package.id).count()
                    review_comment = [review.comment for review in Review.query.join(ServiceRequest).filter(ServiceRequest.package_id == package.id).all()]
                    review_comment = review_comment[:3] if review_comment else None
                    
                    packages.append({
                        'package_id': package.id or 'Unknown Package',
                        'name': package.name or 'Unknown Package',
                        'service_name': service_name,
                        'professional_name': professional_name,
                        'professional_id': package.professional_id or 'Not Assigned',
                        'price': package.price or 'Not Assigned',
                        'phone': phone,
                        'experience': experience_years,
                        'rating': round(avg_rating, 1) if avg_rating else 'Unrated',
                        'reviews': review_count if review_count else '0',
                        'comment': review_comment if review_comment else '',
                        'type': service_type if service_type else 'Unknown type'
                    })                 
       
        return render_template('services/saved_pack.html',
                               username=session['username'],
                               package_data=packages)
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
    
# customer profile 
@app.route('/customer_profile/<string:edit_p>', methods=['GET', 'POST'])
def customer_profile(edit_p):
    if not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'GET' and session.get('userole') == 'customer':
        current_cust = User.query.filter_by(username=session['username']).first()
        
        if current_cust : 
            
            cust_data = {
                'name': current_cust.username,
                'email': current_cust.email,
                'phone': current_cust.phone,
                'address': current_cust.address,
                'pincode': current_cust.pincode,
                'type': current_cust.type
            }
            
        if edit_p == 'v':
            return render_template('cust_profile.html',
                                   username=session['username'],
                                   edit_enable=False,
                                   cust_data=cust_data)
        
        elif session.get('logged_in') and edit_p == 'edit':
            return render_template('cust_profile.html',
                                   username=session['username'],
                                   
                                   cust_data=cust_data,
                                   edit_enable=True)
    elif request.method == 'GET' and session.get('userole') == 'admin':
        current_cust = User.query.get(edit_p)
        cust_data = {
            'name': current_cust.username,
            'email': current_cust.email,
            'phone': current_cust.phone,
            'address': current_cust.address,
            'pincode': current_cust.pincode,
            'type': current_cust.type
        }
        return render_template('cust_profile.html',
                                   username=current_cust.username,
                                   cust_data=cust_data,
                                   edit_enable=False,
                                   admin=True)
        
    
    elif session.get('logged_in') and session.get('userole') == 'professional':
        return "<h1>You don't have access to this page</h1>"
    
    
    
    elif session.get('logged_in') and request.method == 'POST':
        current_cust = User.query.filter_by(username=session['username']).first()
        oldn = current_cust.username
        
        if request.form.get('cust_name'):
            
            
            profile_pic = os.path.join(current_app.static_folder, 'assets', 'pics', 'custp', f"{oldn}.png")
           
                                                
            newn = request.form.get('cust_name')
            
            new_path = os.path.join(current_app.static_folder, 'assets', 'pics', 'custp', f"{newn}.png")
            
            if os.path.exists(profile_pic):
                os.rename(profile_pic, new_path)
            
            session['username'] = request.form.get('cust_name')
            current_cust.username = request.form.get('cust_name')
            
            
        if request.form.get('cust_add'):
            current_cust.address = request.form.get('cust_add')
        
        if request.form.get('cust_phone'):
            current_cust.phone = request.form.get('cust_phone')
        
        if request.form.get('cust_pincode'):
            current_cust.pincode = request.form.get('cust_pincode')
        
        try:
            db.session.commit()
            flash('Profile data updated successfully', 'success')
            if not request.files['profile_pic'] :                
                return redirect(url_for('customer_profile', edit_p='v'))
           
        except Exception as e:
            db.session.rollback()
            
            flash(f'An error occurred while updating: {str(e)}', 'error')
            return redirect(url_for('customer_profile', edit_p='v'))
            
            
        pic = request.files['profile_pic']
        
        if pic and pic.filename != '':
            
            # Securing filename
            new_filename = secure_filename(f"{current_cust.username}.png")
            
            #upload dir
            upload_folder = os.path.join(current_app.static_folder, 'assets', 'pics', 'custp')
            
            
            os.makedirs(upload_folder, exist_ok=True)
            
            
            picloc = os.path.join(upload_folder, new_filename)
                        
            # Saving
            pic.save(picloc)
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('customer_profile', edit_p='v'))                
            
        
        else : 
            
            flash('Icon not uploaded', 'error')
            return redirect(url_for('customer_profile', edit_p='v'))        
        
       


# customer search
@app.route('/cust_search', methods=['GET', 'POST'])
def cust_search():
    if not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"

    packages = []

    if request.method == 'GET' and session.get('logged_in') and session.get('userole') == 'customer':
        search_text = request.args.get('search_text', '').strip()
        pricef = request.args.get('pricef', '').strip()
        xpf = request.args.get('xpf', '').strip()
        servicef = request.args.get('servicef', '').strip()
       

        
        package_data = ServicePackage.query.join(Professional, ServicePackage.professional_id == Professional.id)
        packages = []
        
        # package details       
        if package_data: 
            for p in package_data:
                service_name = Service.query.get(p.service_id).name
                professional_name = Professional.query.get(p.professional_id).p_name
                phone = Professional.query.get(p.professional_id).p_phone
                experience_years = Professional.query.get(p.professional_id).experience_years
                packages.append({
                    'package_id': p.id or 'Unknown Package',
                    'name': p.name or 'Unknown Package',
                    'service_name': service_name,
                    'professional_name': professional_name,
                    'professional_id': p.professional_id or 'Not Assigned',
                    'price': p.price or 'Not Assigned',
                    'phone': phone,
                    'experience': experience_years,
                })
            
        packages_copy = packages.copy()
        
        # search filters 
        if search_text or pricef or xpf or servicef:
            
            if search_text:
                packages = [p for p in packages if search_text.lower() in p['name'].lower()
                                        or search_text.lower() in p['professional_name'].lower()
                                        or search_text.lower() in str(p['price']).lower()
                                        or search_text.lower() in p['service_name'].lower()] 
            
            if pricef:
                if pricef != 'max' : 
                    packages = [p for p in packages if float(pricef)-500 <= p['price'] <= float(pricef)]
                elif pricef == 'max':
                    packages = [p for p in packages if p['price'] >= 1500]
            
            if servicef:
                packages = [p for p in packages if servicef in p['service_name']]
                
            if xpf:
                packages = [p for p in packages if xpf in p['experience'] ] 
                  
        else : 
            packages = packages_copy                            


        return render_template('cust_search.html', username=session['username'],
                               packages=packages, services = Service.query.all(),
                               searched_text = search_text,
                               f_price = pricef, f_xp = xpf, f_service = servicef)

    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))


    
# customer summary 
@app.route('/cust_summary', methods=['GET'])
def cust_summary():
    if not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    if session.get('logged_in') and session.get('userole') == 'customer':
        
        # implement values stats 
        current_user = User.query.filter_by(username=session['username']).first()
        total_booked_requests = ServiceRequest.query.filter_by(customer_id=current_user.id).count()
        services_used = ServiceRequest.query.join(ServicePackage, ServicePackage.id == ServiceRequest.package_id).filter(ServiceRequest.customer_id == current_user.id).with_entities(ServicePackage.service_id).distinct().count()
        packages_used = ServicePackage.query.join(ServiceRequest, ServicePackage.id == ServiceRequest.package_id).filter(ServiceRequest.customer_id == current_user.id).distinct().count()
       
        
        # charts data 
        
        #popular requests
        popular_requests = ServicePackage.query.join(ServiceRequest, ServicePackage.id == ServiceRequest.package_id) \
            .filter(ServiceRequest.customer_id == current_user.id) \
            .with_entities(ServicePackage.name, func.count(ServiceRequest.id)) \
            .group_by(ServicePackage.name).all()
        
        request_data = []
        request_labels = []
        for r in popular_requests:
            if len(request_data) <3:
                request_data.append(r[1])
        
        for r in popular_requests:
            if len(request_labels) <3:
                request_labels.append(r[0])
            
        # all requests 
        all_req = ServiceRequest.query.with_entities(ServiceRequest.status, func.count(ServiceRequest.id)) \
                    .filter_by(customer_id=current_user.id).group_by(ServiceRequest.status).all()
                    
        req_data = []
        req_labels = []
        for r in all_req:
            if len(req_data) <4:
                req_data.append(r[1])
            
        for r in all_req:
            if len(req_labels) <4:
                req_labels.append(r[0])      
            
        
        
        
        # professinals
        pro_q = db.session.query(Professional.p_name, func.count(ServiceRequest.id)).join(ServiceRequest).filter(ServiceRequest.customer_id == current_user.id).group_by(Professional.p_name).all()
        
        pro_data =[]
        pro_labels = []
        for p in pro_q:
            if len(pro_data) <3:
                pro_data.append(p[1])
        for p in pro_q:
            if len(pro_data) <3:
                pro_labels.append(p[0])
        
        
        
        return render_template('cust_summary.html', username=session['username'],
                               total_booked_requests=total_booked_requests,
                               services_used=services_used, packages_used=packages_used,
                               request_data=request_data, request_labels=request_labels,
                               req_data=req_data, req_labels=req_labels,
                               pro_labels=pro_labels, pro_data=pro_data)
                               
                               
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
    


#CRUD for customer

# creating service request
@app.route('/create_service_request', methods=['POST'])
def create_service_request():
    if not session.get('logged_in') or 'username' not in session:
        flash('Please log in to create a service request', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"

    package_id = request.form.get('package_id')
    professional_id = request.form.get('professional_id')
    time = request.form.get('time')
    date = request.form.get('date')

    # Combine date and time
    date_time_str = f"{date} {time}"
    date_time_obj = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M')

    # Get the current user's ID
    current_user = User.query.filter_by(username=session['username']).first()

    if not current_user:
        flash('User not found', 'error')
        return redirect(url_for('cust_dash'))

    # Create new service request
    new_request = ServiceRequest(
        customer_id=current_user.id,
        package_id=package_id,
        professional_id=professional_id,
        date_of_request=datetime.now(IST),
        date_of_completion=date_time_obj,
        status='Requested'
    )

    try:
        db.session.add(new_request)
        db.session.commit()
        flash('Service request created successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    

    return redirect(url_for('cust_dash'))


# updating service request

@app.route('/update_service_request/<int:service_request_id>/<status>', methods=['GET', 'POST'])
def update_service_request(service_request_id, status):
    if not session.get('logged_in') or 'username' not in session:
        flash('Please log in to update the service request', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"

    if request.method == 'GET':
        current_user = User.query.filter_by(username=session['username']).first()
        service_data = ServiceRequest.query.filter_by(id=service_request_id).first()
        package_name = ServicePackage.query.join(ServiceRequest).filter(ServiceRequest.id == service_request_id).with_entities(ServicePackage.name).first()
        professional_name = Professional.query.join(ServiceRequest).filter(ServiceRequest.id == service_request_id).with_entities(Professional.p_name).first()
        date_time = ServiceRequest.query.with_entities(ServiceRequest.date_of_completion).filter(ServiceRequest.id == service_request_id).first()
        if not service_data:
            flash('Service request not found', 'error')
            return redirect(url_for('cust_dash'))
        
        return render_template('update_service_req.html',
                               service_request=service_request_id,
                               status=status, 
                                name=package_name[0],
                                professional_name=professional_name[0],
                                date_time=date_time[0])

    elif request.method == 'POST':
        new_time = request.form.get('time')
        new_date = request.form.get('date')
        new_date_time_str = f"{new_date} {new_time}"
        new_date_time_obj = datetime.strptime(new_date_time_str, '%Y-%m-%d %H:%M')
        
        try:
            db.session.query(ServiceRequest).filter(ServiceRequest.id == service_request_id).update({
                ServiceRequest.date_of_completion: new_date_time_obj,
                ServiceRequest.status: 'Requested'
            })
            db.session.commit()
            flash('Service request updated successfully', 'success')
            return redirect(url_for('cust_dash'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('cust_dash'))
                    

#closing service request
@app.route('/close_service_request/<int:service_request_id>', methods=['GET', 'POST'])
def close_service_request(service_request_id):
    if not session.get('logged_in') or 'username' not in session:
        flash('Please log in to close the service request', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':
        service_request = ServiceRequest.query.get(service_request_id)
        service_id = service_request_id
        professional_name = Professional.query.get(service_request.professional_id)
        if professional_name:
            professional_name = professional_name.p_name
        package_name = ServicePackage.query.get(service_request.package_id)
        if package_name:
            package_name = package_name.name
        
        if not service_request:
            flash('Service request not found', 'error')
            return redirect(url_for('cust_dash'))
        return render_template('close_service_request.html',name = package_name,
                               service_id=service_id,
                               professional_name=professional_name,
                               date_time = service_request.date_of_completion)   
    
    elif request.method == 'POST':
        service_request = ServiceRequest.query.get(service_request_id)
        rating = request.form.get('rating')
        comment = request.form.get('feedback')
        if not service_request:
            flash('Service request not found', 'error')
            return redirect(url_for('cust_dash'))
        try:
            db.session.query(ServiceRequest).filter(ServiceRequest.id == service_request_id).update({
                ServiceRequest.status: 'Completed'
            })
            
            db.session.add(Review(service_request_id=service_request_id, rating=rating, comment=comment))
            
            db.session.commit()
            flash('Service request closed successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('cust_dash'))
                       
            
           
        
    
       

# CANCELLING - deleting service request
@app.route('/cancel_service_request/<int:service_request_id>', methods=['GET', 'POST'])
def cancel_service_request(service_request_id):
    if  not session.get('logged_in') or 'username' not in session:
        flash('Please log in to cancel the service request', 'error')   
        return redirect(url_for('login'))
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    else : 
        service_request = ServiceRequest.query.get(service_request_id)
        if not service_request:
            flash('Service request not found', 'error')
            return redirect(url_for('cust_dash'))
        db.session.delete(service_request)
        db.session.commit()
        flash('Service request cancelled successfully', 'success')
        return redirect(url_for('cust_dash')) 


#professional routes

# dash for professional
@app.route('/pro_dash', methods=['GET'])
def pro_dash():
    if  not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif session.get('userole') == "professional": 
        
        pro = Professional.query.filter_by(p_name=session['username']).first()
        
        

        my_requests = ServiceRequest.query.filter(ServiceRequest.professional_id == pro.id).all()

        jobs = []
        for r in my_requests:            
            customer = User.query.filter_by(id=r.customer_id).first()
            if customer:
                customer = customer.username
            c_phone = User.query.filter_by(id=r.customer_id).first()
            if c_phone:
                c_phone = c_phone.phone
            package_name = ServicePackage.query.join(ServiceRequest).filter(ServiceRequest.id == r.id).first()
            if package_name:
                package_name = package_name.name
            address = User.query.filter(User.id == r.customer_id).first()
            if address:
                address = address.address
            pincode = User.query.filter(User.id == r.customer_id).first()
            if pincode:
                pincode = pincode.pincode
            jobs.append({
                'service_request_id': r.id,
                'package_name': package_name if package_name else 'Unknown Service',
                'customer_name': customer if customer else 'Not Assigned',   
                'date_time': r.date_of_completion,
                'phone': c_phone if c_phone else "None", 
                'location': address , 
                'pincode': pincode, 
                'status': r.status                
            })
            
        all_packages = ServicePackage.query.filter_by(professional_id=pro.id).all()
        packages = []
        
        if all_packages:
            for package in all_packages:
                service_name = db.session.query(Service.name).join(ServicePackage, Service.id == ServicePackage.service_id).filter(ServicePackage.id == package.id).scalar()
                packages.append({
                    'package_id': package.id,
                    'name': package.name,
                    'service_name': service_name if service_name else 'Unknown Service',
                    'price': package.price,
                    'duration': package.duration,
                    'description': package.description
                })
        flagged_packages = ServicePackage.query.filter_by(professional_id=pro.id, is_flagged=True).all()
        flagged = []
        for pkf in flagged_packages:
            flagged.append(pkf.name)
        
        if flagged_packages:
            flash(f'The following packages have been flagged:  " {", ".join(flagged)} " , please update them', 'error')
        
        # reviews 
        reviews_data = Review.query.join(ServiceRequest, ServiceRequest.id == Review.service_request_id) 
        reviews = []
        reviews_data = Review.query.join(ServiceRequest, ServiceRequest.id == Review.service_request_id) \
            .join(ServicePackage, ServicePackage.id == ServiceRequest.package_id) \
            .filter(ServicePackage.professional_id == pro.id).all()
        if reviews_data:
            for review in reviews_data:
                service_request = ServiceRequest.query.get(review.service_request_id)
                package_name = ServicePackage.query.get(service_request.package_id)
                if package_name:
                    package_name = package_name.name
                customer_name = User.query.get(service_request.customer_id)
                if customer_name:
                    customer_name = customer_name.username
                if service_request and package_name and customer_name:
                    reviews.append({
                    'service_id' : review.service_request_id,
                    'rating': review.rating,
                    'comment': review.comment,
                    'package_name': package_name,
                    'customer_name': customer_name,
                    'date_time': review.date_created
                    })
        
        reviews.reverse()
        return render_template('pro_dash.html',
                               username=session['username'],
                               jobs=jobs, packages=packages,
                               reviews=reviews)
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
    
    
#crud for professional

# updating service request status
@app.route('/accept/<int:service_request_id>', methods=['GET'])
def accept(service_request_id):
    if  not session.get('logged_in') or 'username' not in session:
        flash('Please log in to accept the service request', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':       
        try:
            db.session.query(ServiceRequest).filter(ServiceRequest.id == service_request_id).update({
                ServiceRequest.status: 'Accepted'})
            db.session.commit()
            flash('Service request Accepted', 'success')
            return redirect(url_for('pro_dash'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('pro_dash'))
    
# rejecting service request
@app.route('/reject/<int:service_request_id>', methods=['GET'])
def reject(service_request_id):
    if  not session.get('logged_in') or 'username' not in session:
        flash('Please log in to accept the service request', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':
            
        try:
            db.session.query(ServiceRequest).filter(ServiceRequest.id == service_request_id).update({
                ServiceRequest.status: 'Rejected'})
            db.session.commit()
            flash('Service request Rejected', 'error')
            return redirect(url_for('pro_dash'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('pro_dash'))
    
# final closure of service 
@app.route('/final_closing/<int:service_request_id>', methods=['GET'])
def final_closing(service_request_id):
    if  not session.get('logged_in') or 'username' not in session:
        flash('Please log in to close the service request', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':
        service_request = ServiceRequest.query.get(service_request_id)
        if not service_request:
            flash('Service request not found', 'error')
            return redirect(url_for('pro_dash'))
        try:
            db.session.query(ServiceRequest).filter(ServiceRequest.id == service_request_id).update({
                ServiceRequest.status: 'Closed'
            })
            db.session.commit()
            flash('Service request closed successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('pro_dash'))

# creating a new package 
@app.route('/create_package', methods=['GET','POST'])
def create_package():
    if not session.get('logged_in') or 'username' not in session:
        flash('Please log in to create a package', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':
        service_id = db.session.query(Professional.service_id).filter_by(p_name= session['username']).scalar()
        return render_template('create_package.html', username=session['username'], id=service_id)
    
    elif request.method == 'POST':
        pro = Professional.query.filter_by(p_name=session['username']).first()
        service_id = db.session.query(Professional.service_id).filter_by(p_name= session['username']).scalar()
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        duration = request.form.get('duration')
        
        new_package = ServicePackage(professional_id=pro.id, service_id=service_id, name=name, price=price, description=description, duration=duration)
        
        try:
            db.session.add(new_package)
            db.session.commit()
            flash('Package created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('pro_dash'))
    
# updating package 
@app.route('/update_package<int:package_id>', methods=['GET', 'POST'])
def update_package(package_id):
    if not session.get('logged_in') or 'username' not in session:
        flash('Please log in to update the package', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':
        service_id = db.session.query(Professional.service_id).filter_by(p_name= session['username']).scalar()
        package_name = ServicePackage.query.get(package_id)
        if package_name:
            package_name = package_name.name
        price = ServicePackage.query.get(package_id)
        if price:
            price = price.price
        description = ServicePackage.query.get(package_id)
        if description:
            description = description.description
        duration = ServicePackage.query.get(package_id)
        if duration:
            duration = duration.duration
        
        
        return render_template('update_package.html', username=session['username'], id=service_id,
                               package_id=package_id, name=package_name,
                               price=price, description=description,
                               duration= duration)
    
    elif request.method == 'POST':
        pro = Professional.query.filter_by(p_name=session['username']).first()
        service_id = db.session.query(Professional.service_id).filter_by(p_name= session['username']).scalar()
        name = request.form.get('name')
        price = request.form.get('price')
        description = request.form.get('description')
        duration = request.form.get('duration')
        
        
        try:
            db.session.query(ServicePackage).filter(ServicePackage.id == package_id).update({
                ServicePackage.name: name,
                ServicePackage.price: price,
                ServicePackage.description: description,
                ServicePackage.duration: duration,
                ServicePackage.is_flagged: False
            })
            db.session.commit()
            flash('Package updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('pro_dash'))
        
# deleting package 

@app.route('/delete_package<int:package_id>', methods=[ 'GET','POST'])    
def delete_package(package_id):
    
    if not session.get('logged_in') or 'username' not in session:
        flash('Please log in to delete the package', 'error')
        return redirect(url_for('login'))
    if session.get('userole') == "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    else:       

        # Fetching the service request associated with the package_id
        service_request = ServiceRequest.query.filter(ServiceRequest.package_id == package_id,
                                                      or_(ServiceRequest.status != 'Closed')).all()
        closed_requests = ServiceRequest.query.filter(ServiceRequest.package_id == package_id,
                                                      ServiceRequest.status == 'Closed').all()
        
        if not service_request:       
        
                try:
                    package = ServicePackage.query.get(package_id)                    
                    db.session.delete(package)
                    
                    # dlt review first 
                    for req in closed_requests:                        
                        reviews = Review.query.filter(Review.service_request_id == req.id).all()
                        for review in reviews:
                            db.session.delete(review)
                    # dlt req also 
                    for req in closed_requests:
                        db.session.delete(req)
                        
                    # delete from cust saved packs 
                    req_cust = User.query.filter(User.role=="customer").all()
                    for r in req_cust:
                        saved_packs = r.saved_packs
                        if saved_packs:
                            r.saved_packs = r.saved_packs.replace(f',{package_id}', '').replace(f'{package_id},', '').replace(f'{package_id}', '')            
                        
                    db.session.commit()
                    flash('Package deleted successfully', 'success')
                    
                except Exception as e:
                    db.session.rollback()
                    flash(f'An error occurred: {str(e)}', 'error')
                
                if session['userole'] == 'professional':
                    return redirect(url_for('pro_dash'))
                elif session['userole'] == 'admin':
                    return redirect(url_for('admin'))
        else:       
            flash('Complete requests for this package first', 'error')
            if session['userole'] == 'professional':
                return redirect(url_for('pro_dash'))
            elif session['userole'] == 'admin':
                return redirect(url_for('admin'))
    

# pro search
@app.route('/pro_search', methods=['GET'])
def pro_search():
    if  not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif session.get('userole') == "professional": 
        
        search_text = request.args.get('search_text', '').strip()
        pkg_id = request.args.get('pkgs', '').strip()
        loc = request.args.get('loc', '').strip()
        status = request.args.get('status', '').strip()
        
        
        pro_id = Professional.query.filter_by(p_name=session['username']).first().id
        
        # for packge filter list in template
        pkg_list = ServicePackage.query.filter(ServicePackage.professional_id == pro_id).all()
        pkg_options = []
        for p in pkg_list:
            pkg_options.append({
                'package_id': p.id,
                'name': p.name
            })
            
        # finding package name from filter (pkg id)
        if pkg_id:
            pkgs = ServicePackage.query.get(pkg_id).name
        else :
            pkgs = None
                
        service_requests = ServiceRequest.query.filter(ServiceRequest.professional_id == pro_id).all()
        # Format data for the template
        search_data = []
        for req in service_requests:
            customer = User.query.get(req.customer_id)
            package = ServicePackage.query.get(req.package_id)

            search_data.append({
                'service_request_id': req.id or 'Unknown Request', 
                'package_name': package.name if package else 'Unknown Service',
                'cust_name': customer.username if customer else 'Not Assigned',
                'completion_date': req.date_of_completion,
                'phone': customer.phone if customer else 'none',
                'location': customer.address if customer else 'Not Assigned',
                'pincode': customer.pincode if customer else 'Not Assigned',
                'status': req.status or 'Unknown Status'
            })
        
        search_data.reverse()
        search_data_copy = search_data.copy()
            
        if search_text or pkgs or loc or status:
            
            if search_text:
                search_data = [r for r in search_data if search_text.lower() in r['package_name'].lower()
                                        or search_text.lower() in r['cust_name'].lower()
                                        or search_text.lower() in r['location'].lower()
                                        or search_text.lower() in r['status'].lower()]
            
            if pkgs:
                search_data = [r for r in search_data if pkgs in r['package_name']]
                
            if loc:
                search_data = [r for r in search_data if loc in r['location']]
                
            if status:
                search_data = [r for r in search_data if status in r['status']]
        else : 
            search_data = search_data_copy
            
        
        
        return render_template('pro_search.html',
                               username=session['username'],
                               pkg_options=pkg_options,
                               search_data = search_data,
                               searched_text = search_text, pkg_namef = pkgs, locf = loc, statusf = status)
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))

# pro summary
@app.route('/pro_summary', methods=['GET'])
def pro_summary():
    if  not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    if session.get('userole') != "professional" :
        return "<h1>You don't have access to this page</h1>"
    
    elif session.get('userole') == "professional":    
        current_pro = Professional.query.filter_by(p_name=session['username']).first()
        total_requests = ServiceRequest.query.filter_by(professional_id=current_pro.id).count()
        avg_rating = db.session.query(func.avg(Review.rating)).join(ServiceRequest).filter(ServiceRequest.professional_id == current_pro.id).scalar()
        total_earnings = db.session.query(func.sum(ServicePackage.price)).join(ServiceRequest).filter(ServiceRequest.professional_id == current_pro.id).scalar()
        
        # charts data 
        
        #ratings 
        all_ratings = db.session.query(Review.rating, func.count(Review.id)).join(ServiceRequest).filter(ServiceRequest.professional_id == current_pro.id).group_by(Review.rating).all()
        
        rating_data = []
        rating_labels = []
       
        for r in all_ratings:
            rating_labels.append(r[0])
            rating_data.append(r[1])
       
            
                            
        # all requests 
        all_req = db.session.query(ServiceRequest.status, func.count(ServiceRequest.id)).filter(ServiceRequest.professional_id == current_pro.id).group_by(ServiceRequest.status).all()
        req_data = []
        req_labels = []
        for r in all_req:
            if len(req_data) <4:
                req_data.append(r[1])
                req_labels.append(r[0])      
            
        
        
        
        # top packages 
        top_packages = db.session.query(ServicePackage.name, func.count(ServiceRequest.id)).join(ServiceRequest).filter(ServiceRequest.professional_id == current_pro.id).group_by(ServicePackage.name).all()
        pkg_labels = []
        pkg_data = []
        for p in top_packages:
            if len(pkg_labels) <3:
                pkg_labels.append(p[0])
                pkg_data.append(p[1])
        
        
        return render_template('pro_summary.html', username=session['username'], total_requests=total_requests,
                               avg_rating=avg_rating, total_earnings=total_earnings,
                               req_data=req_data, req_labels=req_labels,
                               rating_data=rating_data,rating_labels=rating_labels,
                               pkg_labels=pkg_labels, pkg_data=pkg_data)
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
   
#pro  profile
@app.route('/pro_profile/<string:edit_p>', methods=['GET','POST'])
def pro_profile(edit_p):
    if  not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'GET' and session.get('userole') == 'professional':
        current_pro = Professional.query.filter_by(p_name=session['username']).first()
        prating = Review.query.join(ServiceRequest, ServiceRequest.id == Review.service_request_id).filter(
                            ServiceRequest.professional_id == current_pro.id if current_pro else None
                                ).with_entities(func.avg(Review.rating).label('avg_rating')).scalar()
        reviewc = Review.query.join(ServiceRequest).filter(ServiceRequest.professional_id == current_pro.id).count()
        
        if current_pro:           
            pro_data = {
                'name': current_pro.p_name,
                'email': current_pro.p_email,
                'phone': current_pro.p_phone,
                'address': current_pro.paddress,
                'pincode': current_pro.p_pincode,
                'service': Service.query.get(current_pro.service_id).name,
                'xp': current_pro.experience_years,
                'doc': current_pro.document_proof,
                
                'rating' : round(prating,1) if prating else 0, 
                
                'rev_count' : reviewc if reviewc else 0

            }
        if edit_p == 'v':          
            return render_template('pro_profile.html', username=session['username'],
                                edit_enable = False,
                                pro_data=pro_data)
            
        elif session.get('logged_in') and edit_p == 'edit':
            current_pro = Professional.query.filter_by(p_name=session['username']).first()
           
            return render_template('pro_profile.html', username=session['username'],
                                pro_data=pro_data,  edit_enable = True )
    
    # customer view 
    elif session.get('userole') != "professional" :
        
        pro_dteail = Professional.query.filter_by(p_name=edit_p).first()
        prating = Review.query.join(ServiceRequest, ServiceRequest.id == Review.service_request_id).filter(
                            ServiceRequest.professional_id == pro_dteail.id if pro_dteail else None
                                ).with_entities(func.avg(Review.rating).label('avg_rating')).scalar()
        reviewc = Review.query.join(ServiceRequest).filter(ServiceRequest.professional_id == pro_dteail.id).count()
                   
        
        if pro_dteail:           
            pro_data = {
                'name': pro_dteail.p_name,
                'email': pro_dteail.p_email,
                'phone': pro_dteail.p_phone,
                'address': pro_dteail.paddress,
                'pincode': pro_dteail.p_pincode,
                'service': Service.query.get(pro_dteail.service_id).name,
                'xp': pro_dteail.experience_years,
                'doc': pro_dteail.document_proof,
                
                'rating' : round(prating,1) if prating else 0, 
                
                'rev_count' : reviewc if reviewc else 0
            }        
                    
        return render_template('pro_profile.html',
                                edit_enable = False,
                                pro_data=pro_data,
                                view_only = True,
                                role = session.get('userole'))
                    
    elif request.method == 'POST':
        current_pro = Professional.query.filter_by(p_name=session['username']).first()
        oldn = current_pro.p_name
        old_doc = current_pro.document_proof
        if request.form.get('pro_name'):
            
            
            profile_pic = os.path.join(current_app.static_folder, 'assets', 'pics',  f"{oldn}.png")
           
                                                
            newn = request.form.get('pro_name')
            
            new_path = os.path.join(current_app.static_folder, 'assets', 'pics', f"{newn}.png")
            
            if os.path.exists(profile_pic):
                os.rename(profile_pic, new_path)
                
            #updated doc name 
            if old_doc:
                old_doc = os.path.join(current_app.static_folder, 'docs',  f"{oldn}.pdf")
                new_doc = os.path.join(current_app.static_folder,  'docs', f"{newn}.pdf".replace(' ', '_'))
                if os.path.exists(old_doc):
                    os.rename(old_doc, new_doc)
                current_pro.document_proof = f"{newn}.pdf".replace(' ', '_')
            
            session['username'] = request.form.get('pro_name')
            current_pro.p_name = request.form.get('pro_name')        
                
        if request.form.get('pro_add'):
            current_pro.paddress = request.form.get('pro_add')
        
        if request.form.get('pro_phone'):
            current_pro.p_phone = request.form.get('pro_phone')
        
        if request.form.get('pro_pincode'):
            current_pro.p_pincode = request.form.get('pro_pincode')
            
        
            
        try:
            db.session.commit()
            flash('Profile data updated successfully', 'success')
            if not request.files['profile_pic'] :
                return redirect(url_for('pro_profile', edit_p='v'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        
            
        pic = request.files['profile_pic']
                         
        if pic and allowed_file(pic.filename):
            if pic.content_length > app.config['MAX_CONTENT_LENGTH']:
                flash('Icon size too large', 'error')
                return redirect(url_for('pro_profile', edit_p='edit'))
            
            # Secure filename
            new_filename = secure_filename(f"{current_pro.p_name}.png")
            
            #upload folder
            upload_folder = os.path.join(current_app.static_folder, 'assets', 'pics')
            
            #existance of upload folder
            os.makedirs(upload_folder, exist_ok=True)
            
            
            picloc = os.path.join(upload_folder, new_filename)
            
            
           #saving
            pic.save(picloc)
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('pro_profile', edit_p='v'))   
        
            
        else :             
            flash('Icon not uploaded', 'error')
            return redirect(url_for('pro_profile', edit_p='edit'))          
            
    
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))
    



# admin routes 

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if  not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    if session.get('logged_in') and session.get('userole') == 'admin':
      
        if request.method == 'GET':
            
            search_text = request.args.get('search_text', '').strip()
            service_f = request.args.get('service_f', '').strip()
            price = request.args.get('price_f', '').strip()
            loc = request.args.get('loc', '').strip()
            exception = request.args.get('except', '').strip()
            
            
                            
            professionals_data = Professional.query.filter_by(is_approved=False).all()
           
            
            professionals = []
            for pro in professionals_data:
                
                service = Service.query.get(pro.service_id)
                
                if not pro.id or not service:
                    continue
                professionals.append({
                    'professional_id': pro.id,
                    'name':  pro.p_name if pro else 'Unknown Professional',
                    'email': pro.p_email if pro else 'Unknown Email',
                    'phone': pro.p_phone  if pro.p_phone else 'Unknown Phone',
                    'address': pro.paddress if pro.paddress else 'Unknown Address',
                    'pincode': pro.p_pincode if pro.p_pincode else 'Unknown Pincode',
                    'service': service.name if service else 'Unknown Service',
                    'experience': pro.experience_years if pro.experience_years else '0',
                    'contact': pro.p_phone if pro.p_phone else 'Unknown Phone',
                    'price': pro.base_price if pro.base_price else 'Unknown Price',
                    'doc': pro.document_proof if pro.document_proof else 'Unknown Document',
                    'approved': 'Yes' if pro.is_approved else 'No',
                    'blocked': 'Yes' if pro.is_blocked else 'No',
                    
                })
                
            
           
            verified_professionals_data = Professional.query.filter_by(is_approved=True).all()
            verified_professionals = []
            
            for p in verified_professionals_data:
                service = Service.query.get(p.service_id)
                
                if not p.id or not service:
                    continue
                
                verified_professionals.append({
                    'professional_id': p.id,
                    'name': p.p_name if p else 'Unknown Professional',
                    'email': p.p_email if p else 'Unknown Email',
                    'phone': p.p_phone if p.p_phone else 'Unknown Phone',
                    'address': p.paddress if p.paddress else 'Unknown Address',
                    'pincode': p.p_pincode if p.p_pincode else 'Unknown Pincode',
                    'service': service.name if service else 'Unknown Service',
                    'experience': p.experience_years,
                    'contact': p.p_phone if p.p_phone else 'Unknown Phone',
                    'price': p.base_price if p.base_price else 'Unknown Price',
                    'doc': p.document_proof if p.document_proof else 'Unknown Document',
                    'approved': 'Yes' if p.is_approved else 'No',
                    'blocked': 'Yes' if p.is_blocked else 'No',
                    
                })
            verified_professionals_copy = verified_professionals.copy()
            
            if search_text or service_f or loc:
                                                    
                if search_text:
                    verified_professionals = [p for p in verified_professionals if search_text.lower() in p['name'].lower()
                                              or search_text.lower() in p['email'].lower()
                                              or search_text.lower() in p['service'].lower() ]
                    

                if service_f:
                    verified_professionals = [p for p in verified_professionals if service_f.lower() in p['service'].lower()]
                    
                
                if loc:
                    verified_professionals = [p for p in verified_professionals if loc.lower() in p['address'].lower() or loc.lower() in str(p['pincode']).lower()]
            
            if len(verified_professionals) == 0 and exception == 'professional':
                        verified_professionals = verified_professionals_copy
            
            
            customers_data = User.query.filter_by(role='customer').all()
            customers = []
            for c in customers_data:
                customers.append({
                    'customer_id': c.id,
                    'name': c.username if c else 'Unknown Customer',
                    'email': c.email if c else 'Unknown Email',
                    'phone': c.phone if c.phone else 'Unknown Phone',
                    'address': c.address if c.address else 'Unknown Address',
                    'pincode': c.pincode if c.pincode else 'Unknown Pincode',
                    'type': c.type if c.type else 'Unknown Type',
                    'is_approved': 'Yes' if c.is_approved else 'No',
                    'is_blocked': 'Yes' if c.is_blocked else 'No'
                })
            original_customers = customers.copy()

            if search_text or loc:
                if search_text:
                    customers = [c for c in customers if search_text.lower() in c['name'].lower()
                                 or search_text.lower() in c['email'].lower()
                                 or search_text.lower() in c['type'].lower()
                                 or search_text.lower() in str(c['pincode']).lower()]
                  
              
                                     
                if loc:
                    customers = [c for c in customers if loc.lower() in c['address'].lower() or loc.lower() in str(c['pincode']).lower()]
                   
            if len(customers) == 0 and exception == 'customer':
                customers = original_customers
                
            service_requests_data = ServiceRequest.query.all()
            service_requests_details = []
            for r in service_requests_data:
                
                if not r.package_id :
                    continue
                
                if r.package_id :
                    
                    if not ServicePackage.query.get(r.package_id) :
                        continue
                
                
                
                customer_name = User.query.get(r.customer_id).username 
                professional_name = Professional.query.get(r.professional_id).p_name
                package = ServicePackage.query.get(r.package_id).name  
                service_name = Service.query.get(ServicePackage.query.get(r.package_id).service_id).name 
                req_price = ServicePackage.query.get(r.package_id).price
                location = User.query.get(r.customer_id).address
                rating = Review.query.filter_by(service_request_id=r.id).first().rating if Review.query.filter_by(service_request_id=r.id).first() else 'Not Rated'
                
                service_requests_details.append({
                    'service_request_id': r.id,
                    'service_name' : service_name if service_name else 'Unknown Service',
                    'customer': customer_name if customer_name else 'Unknown Customer',
                    'professional': professional_name if professional_name else 'Unknown Professional',
                    'package': package if package else 'Unknown Package',
                    'date_of_req': r.date_of_request,
                    'date_of_completion': r.date_of_completion,
                    'price': req_price if req_price else 'Unknown Price',
                    'location': location if location else 'Unknown Location',
                    'rating': rating if rating else 'Not Rated',
                    'status': r.status
                })
                
                service_requests_details.reverse()
                service_req_copy =  service_requests_details.copy()
                
            if search_text or service_f or price or loc:
                if search_text:
                    service_requests_details = [r for r in service_requests_details if search_text.lower() in r['customer'].lower()
                                                or search_text.lower() in r['professional'].lower()
                                                or search_text.lower() in r['service_name'].lower()
                                                or  search_text.lower() in r['package'].lower()
                                                or search_text.lower() in r['status'].lower()
                                                or search_text.lower() in str(r['rating']).lower()]
                
                if service_f:
                    service_requests_details = [r for r in service_requests_details if service_f.lower() in r['service_name'].lower()]
                
                if price:
                    service_requests_details = [r for r in service_requests_details if float(price)-500 <= r['price'] <= float(price)]
                if loc:
                    service_requests_details = [r for r in service_requests_details if loc.lower() in r['location'].lower()]
            
            if len(service_requests_details) == 0 and exception == 'requests':
                service_requests_details = service_req_copy   
                
                                
            service_data = Service.query.all()
            service_details = []
            for s in service_data:
                service_details.append({
                    'service_id': s.id,
                    'service_name': s.name,
                    'base_price': s.base_price,
                    'description': s.description,
                    'category': s.category
                })
            
            service_copy = service_details.copy()    
            
            if search_text or service_f or price:
                if search_text:
                    service_details = [s for s in service_details if search_text.lower() in s['service_name'].lower()
                                       or search_text.lower() in s['category'].lower()
                                       or search_text.lower() in str(s['base_price']).lower()
                                       or search_text.lower() in s['description'].lower()]
                
                if service_f:
                    service_details = [s for s in service_details if service_f.lower() in s['service_name'].lower()]
                
                if price:
                    service_details = [s for s in service_details if float(price)-500 <= s['base_price']<= float(price)]
              
            if len(service_details) == 0 and exception == 'services':
                service_details = service_copy
                         
            packages_data = ServicePackage.query.all()
            packages = []
            for p in packages_data:
                service_name = Service.query.get(p.service_id).name if Service.query.get(p.service_id) else 'Unknown Service'
                professional_name = Professional.query.get(p.professional_id).p_name if Professional.query.get(p.professional_id) else 'Unknown Professional'
                packages.append({
                    'package_id': p.id if p.id else 'Unknown Package',
                    'package_name': p.name if p.name else 'Unknown Package',
                    'service_name': service_name if service_name else 'Unknown Service',
                    'professional_name': professional_name if professional_name else 'Unknown Professional',
                    'price': p.price if p.price else 'Unknown Price',
                    'duration': p.duration if p.duration else 'Unknown Duration',
                    'description': p.description if p.description else 'Unknown Description',
                })
            
            pack_copy = packages.copy()
                
            if search_text or service_f or price:
                if search_text:
                    packages = [p for p in packages if search_text.lower() in p['package_name'].lower()
                                or search_text.lower() in p['service_name'].lower()
                                or search_text.lower() in p['professional_name'].lower()
                                or search_text.lower() in str(p['price']).lower()
                                or search_text.lower() in p['duration'].lower()
                                or search_text.lower() in p['description'].lower()]
                
                if service_f:
                    packages = [p for p in packages if service_f.lower() in p['service_name'].lower()]
                
                if price:
                    packages = [p for p in packages if float(price)-500 <= p['price'] <= float(price)]
                    
            if len(packages) == 0 and exception == 'packages':
                packages = pack_copy
                
            # statistics data summary 
            total_users = User.query.filter_by(role = 'customer').count()
            plat_users = User.query.filter_by(type='Platinum').count()
            total_professionals = Professional.query.filter_by(is_approved=True).count()
            total_services = Service.query.count()
            total_service_requests = ServiceRequest.query.count()
            total_revenue = ServicePackage.query.with_entities(func.sum(ServicePackage.price)).scalar()
            completed_requests = ServiceRequest.query.filter_by(status='Completed').count()
            closed_requests = ServiceRequest.query.filter_by(status='Closed').count()
            pending_services = ServiceRequest.query.filter(or_(ServiceRequest.status == 'Requested',
                                                              ServiceRequest.status == 'Accepted')).count()
            
            # charts data 
            
            #ratings and reviews 
            
            overall_ratings = db.session.query(Review.rating, func.count(Review.id)).group_by(Review.rating).all()
            ratings_data = []
            ratings_labels = []
            for r in overall_ratings:
                ratings_data.append(r[1])
                ratings_labels.append(str(r[0]))
                
           
            
            ratings_by_service = db.session.query(ServicePackage.name,func.avg(Review.rating).label('avg_rating')).select_from(ServicePackage).join(ServiceRequest).join(Review).group_by(ServicePackage.name).all()
            pkg_data = []
            pkg_labels = []
            for r in ratings_by_service:
                pkg_data.append(r[1])
                pkg_labels.append(r[0])
           
            
            #all requests summary
            all_requests = db.session.query(ServiceRequest.status, func.count(ServiceRequest.id)).group_by(ServiceRequest.status).all()            
            req_data = []
            req_labels = []
            for r in all_requests:
                req_data.append(r[1])
                req_labels.append(r[0])
           
            
           
            return render_template('admin.html',
                                username=session['username'],
                                professionals=professionals,
                                verified_professionals=verified_professionals,
                                customers_data=customers,
                                packages=packages,
                                service_requests_details=service_requests_details,
                                service_details = service_details,
                                    total_users=total_users,
                                    plat_users=plat_users,
                                total_professionals=total_professionals,
                                total_services=total_services,
                                total_service_requests=total_service_requests,
                                total_revenue=total_revenue,
                                completed_requests=completed_requests,
                                closed_requests=closed_requests,
                                pending_services=pending_services,
                                #charts data
                                ratings_data=ratings_data,ratings_labels=ratings_labels,
                                pkg_data=pkg_data, pkg_labels=pkg_labels,
                                req_data=req_data, req_labels=req_labels,
                                # for filter service cat :
                                service_cat = service_copy ) 
            
    else: 
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))

# request approval for professional
@app.route('/approve_professional', methods=['POST'])
def approve_professional():
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to approve the professional', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
       
    elif request.method == 'POST':
        professional_id = request.form.get('professional_id')
        professional = Professional.query.get(professional_id)
        if not professional:
            flash('Professional not found', 'error')
            return redirect(url_for('admin'))
        
        try:
            db.session.query(Professional).filter(Professional.id == professional_id).update({
                Professional.is_approved: True, Professional.is_blocked: False
            })
            db.session.commit()
            flash('Professional approved successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

# rejecting request 
@app.route('/reject_request', methods=['POST'])
def reject_request():
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to approve the professional', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
       
    elif request.method == 'POST':
        professional_id = request.form.get('professional_id')
        professional = Professional.query.get(professional_id)
        if not professional:
            flash('Professional not found', 'error')
            return redirect(url_for('admin'))
        
        try:
            db.session.query(Professional).filter(Professional.id == professional_id).delete()
            db.session.commit()
            flash('Professional Rejected', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

# request blocking for professional
@app.route('/block_professional', methods=['POST'])
def block_professional():
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to block the professional', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'POST':
        professional_id = request.form.get('professional_id')
        professional = Professional.query.get(professional_id)
        if not professional:
            flash('Professional not found', 'error')
            return redirect(url_for('admin'))
        
        try:
            db.session.query(Professional).filter(Professional.id == professional_id).update({
                Professional.is_blocked: True, Professional.is_approved: False
            })
            db.session.commit()
            flash('Professional blocked successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('admin'))
  
# blocking customers 
@app.route('/block_customer/<int:customer_id>', methods=['GET'])
def block_customer(customer_id):
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to block the customer', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    else:
       
        customer = User.query.get(customer_id)
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('admin'))
        
        try:
            db.session.query(User).filter(User.id == customer_id).update({
                User.is_blocked: True, User.is_approved: False
            })
            db.session.commit()
            flash('Customer blocked successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('admin'))  
# repermitting customers
@app.route('/unblock_customer/<int:customer_id>', methods=['GET'])
def unblock_customer(customer_id):
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to unblock the customer', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    else:
       
        customer = User.query.get(customer_id)
        if not customer:
            flash('Customer not found', 'error')
            return redirect(url_for('admin'))
        
        try:
            db.session.query(User).filter(User.id == customer_id).update({
                User.is_blocked: False, User.is_approved: True
            })
            db.session.commit()
            flash('Customer unblocked successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('admin'))
    
# new service creation 
@app.route('/create_service', methods=['GET','POST'])
def create_service():
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to create a service', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    elif request.method == 'GET':
        return render_template('create_service.html')
    
    elif request.method == 'POST':
       
        name = request.form.get('name')
        base_price = request.form.get('base_price')
        description = request.form.get('description')
        category = request.form.get('category')
        icon = request.files['file']
           
        
        new_service = Service(name=name, base_price=base_price, description=description, category=category)
        
        try:
            db.session.add(new_service)
            db.session.commit()
           
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return redirect(url_for('create_service'))
            
        if icon and allowed_file(icon.filename):
            if icon.content_length > app.config['MAX_CONTENT_LENGTH']:
                flash('Icon size too large', 'error')
                return redirect(url_for('create_service'))

            # service name as the icon filename            
            new_filename = f"{name}.png"  
            # existance of folder
            upload_folder = os.path.join(current_app.static_folder, 'assets', 'icons')
            iconloc = os.path.join(upload_folder, secure_filename(new_filename))
            icon.save(iconloc)
            
            flash('Service created successfully!', 'success')
            return redirect(url_for('admin'))
        else : 
            flash('Icon not uploaded', 'error')
            return redirect(url_for('create_service'))
        
            
        

# update service 
@app.route('/update_service/<int:service_id>', methods=['GET', 'POST'])
def update_service(service_id):
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to update the service', 'error')
        return redirect(url_for('login'))
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    if request.method == 'GET':
        service = Service.query.get(service_id)
        if not service:
            flash('Service not found', 'error')
            return redirect(url_for('admin'))
        service_name = service.name
        s_id = service.id
        base_price = service.base_price
        desc = service.description
        return render_template('update_service.html', service_name=service_name, service_id=s_id,
                               base_price=base_price, description=desc)
    
    elif request.method == 'POST':
        name = request.form.get('name')
        base_price = request.form.get('base_price')
        description = request.form.get('description')
        category = request.form.get('category')
        service_name = Service.query.get(service_id)
        if service_name:
            service_name = service_name.name
        old_icon_loc = os.path.join(current_app.static_folder, 'assets', 'icons', f"{service_name}.png".replace(' ', '_'))
        new_icon_loc = os.path.join(current_app.static_folder, 'assets', 'icons', f"{name}.png".replace(' ', '_'))
        if os.path.exists(old_icon_loc):
            os.rename(old_icon_loc, new_icon_loc)
        
        
        try:
            db.session.query(Service).filter(Service.id == service_id).update({
                Service.name: name,
                Service.base_price: base_price,
                Service.description: description,
                Service.category: category
            })
            db.session.commit()
            flash('Service updated successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('admin'))

# delete service
@app.route('/delete_service/<int:service_id>', methods=['GET'])
def delete_service(service_id):
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to delete the service', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    else:
                
        #service requests associated with the service_id
        active_requests = ServiceRequest.query.filter((ServiceRequest.status != 'Closed')).with_entities(ServiceRequest.package_id).all()
        active_package_ids = [request.package_id for request in active_requests]
        asc_packages = ServicePackage.query.filter(ServicePackage.id.in_(active_package_ids)).all()
        service_pending = [Service.query.get(package.service_id).id for package in asc_packages]
       
        
        
        professionals = Professional.query.filter(Professional.service_id == service_id).all()
        
        if service_id != service_pending and not professionals:
            try:
                service = Service.query.get(service_id)
                db.session.delete(service)
                                 
                db.session.commit()
                flash('Service deleted successfully', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'error')
                
            
            return redirect(url_for('admin'))
        if service_pending == service_id:
            flash('Complete requests for this service first', 'error')
            return redirect(url_for('admin'))
        if professionals:
           flash('There are professionals in this service', 'error')
           return redirect(url_for('admin'))


# service packages CRUD

# flag package
@app.route('/flag_package/<int:package_id>', methods=['GET','POST'])
def flag_package(package_id):
    
    if  not session['logged_in'] or 'username' not in session:
        flash('Please log in to flag the package', 'error')
        return redirect(url_for('login'))
    
    if session.get('userole') != "admin" :
        return "<h1>You don't have access to this page</h1>"
    
    package = ServicePackage.query.get(package_id)
    if not package:
        flash('Package not found', 'error')
        return redirect(url_for('admin'))
    else:
        try:
            db.session.query(ServicePackage).filter(ServicePackage.id == package_id).update({
                ServicePackage.is_flagged: True
            })
            db.session.commit()
            flash('Package flagged successfully', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
    
    return redirect(url_for('admin'))
    
    
    
# service packages routes
#packages
@app.route('/packages<int:service_id>', methods=['GET'])
def packages(service_id):
    if  not session.get('logged_in') or 'username' not in session:
        return redirect(url_for('login'))
    
    if session.get('userole') != "customer" :
        return "<h1>You don't have access to this page</h1>"
    
    elif session.get('logged_in') and session.get('userole') == 'customer':  
        # findig service packages
        packages = ServicePackage.query.filter_by(service_id=service_id).all()
        service_name = Service.query.get(service_id).name
        #data for template
        package_data = []
        for package in packages:
            professional = Professional.query.get(package.professional_id)
            
            
            avg_rating = Review.query.join(ServiceRequest, ServiceRequest.id == Review.service_request_id).filter(
                            ServiceRequest.package_id == package.id
                                ).with_entities(func.avg(Review.rating).label('avg_rating')).scalar()
            
            review_count = Review.query.join(ServiceRequest).filter(ServiceRequest.package_id == package.id).count()
            review_comment = [review.comment for review in Review.query.join(ServiceRequest).filter(ServiceRequest.package_id == package.id).all()]
            review_comment = review_comment[:3] if review_comment else None
            service_type = Service.query.get(service_id).category
            if service_type == 'normal':
                service_type = 'Regular Service'
            
            package_detail = {
                'name': package.name,
                'professional_name': professional.p_name if professional else 'N/A',
                'experience': professional.experience_years if professional else 'N/A',
                'base_price': package.price,
                'rating': round(avg_rating, 1) if avg_rating else 'Unrated',
                'reviews' : review_count if review_count else '0',
                'package_id': package.id,
                'professional_id': professional.id if professional else None,  
                'comment': review_comment if review_comment else '',
                'type' :  service_type if service_type else 'Unknown type'
            }
            package_data.append(package_detail)
            
            

        return render_template('services/packages.html',
                               package_data=package_data,
                               service = service_name)
    else:
        flash('Please login to access this page', 'error')
        return redirect(url_for('login'))

