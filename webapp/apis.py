from flask_restful import Resource, Api
from flask import request, session
from flasgger import Swagger

from flask.json.provider import DefaultJSONProvider as JSONEncoder

from . import app, db
from .models import *
from werkzeug.security import generate_password_hash, check_password_hash

api = Api(app)
swagger = Swagger(app, template_file='static/swagger_qwix.json')

@app.route('/apidocs')
def apidocs():
    return swagger.render_template()

class LoginAPI(Resource):
    def post(self):
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role')

        if role == "professional":
            professional = Professional.query.filter_by(p_email=email).first()
            if professional and check_password_hash(professional.ppassword, password) and professional.is_approved:
                session['username'] = professional.p_name
                session['pro_id'] = professional.id
                session['logged_in'] = True
                session['userole'] = "professional"
                session['saved_packages'] = []
                return {"message": "Login successful", "username": professional.p_name, "role": "professional"}, 200
            elif professional and check_password_hash(professional.ppassword, password) and professional.is_blocked:
                return {"message": "Your account is blocked"}, 403
            else:
                return {"message": "Invalid credentials or your request was rejected"}, 401
        else:
            user = User.query.filter_by(email=email, role=role).first()
            if user and (not user.is_blocked) and user.is_approved and check_password_hash(user.password, password):
                session['username'] = user.username
                session['user_id'] = user.id
                session['logged_in'] = True
                session['userole'] = role
                return {"message": "Login successful", "username": user.username, "role": role}, 200
            elif user and user.is_blocked:
                return {"message": "Your account is blocked"}, 403
            else:
                return {"message": "Invalid email or password"}, 401

api.add_resource(LoginAPI, '/api/login')


class LogoutAPI(Resource):
    def post(self):
        session.clear()
        return {"message": "Logged out successfully"}, 200

api.add_resource(LogoutAPI, '/api/logout')


class RegisterAPI(Resource):
    def post(self):
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = generate_password_hash(data.get('password'))
        address = data.get('address')
        pincode = data.get('pincode')
        role = data.get('role')

        existing_user = User.query.filter_by(email=email).first()
        existing_pro = Professional.query.filter_by(p_email=email).first()
        if existing_user or existing_pro:
            return {"message": "Email already registered"}, 400

        if role == "customer":
            new_customer = User(username=username, email=email, password=password, address=address, pincode=pincode, role=role)
            db.session.add(new_customer)
            db.session.commit()
            return {"message": "Registration successful"}, 201
        elif role == "professional":
            new_pro = Professional(p_name=username, p_email=email, ppassword=password, paddress=address, p_pincode=pincode)
            db.session.add(new_pro)
            db.session.commit()
            return {"message": "Registration successful"}, 201
        else:
            return {"message": "Invalid role"}, 400

api.add_resource(RegisterAPI, '/api/register')


# user details 
class UserAPI(Resource):
    def get(self, user_id=None):
        if not session.get('logged_in'):
            return {"message": "Authentication required"}, 401
        
        if user_id:
            if session.get('userole') != "admin":
                return {"message": "Permission denied"}, 403
            
            user = User.query.get(user_id)
            if user:
                return {"id": user.id, "username": user.username, "email": user.email}, 200
            return {"message": "User not found"}, 404
        
        else:
            if session.get('userole') != "admin":
                return {"message": "Permission denied"}, 403
            
            users = User.query.all()
            users_list = []
            for user in users:
                users_list.append({"id": user.id, "username": user.username, "email": user.email})
            return {"users": users_list}, 200

    def post(self):
        if not session.get('logged_in') or session.get('userole') == "professional":
            return {"message": "Permission denied"}, 403
        
        data = request.get_json()
        new_user = User(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            address=data['address'],
            pincode=data['pincode'],
            phone=data['phone'],
            role=data['role']
        )
        db.session.add(new_user)
        db.session.commit()
        return {"message": "User created successfully"}, 201
    
api.add_resource(UserAPI, '/api/users', '/api/users/<int:user_id>')




class CustomerDashboardAPI(Resource):
    def get(self):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return {"message": "User not found"}, 404
        
        # Assuming there are some customer-specific details to fetch
        customer_details = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "address": user.address,
            "pincode": user.pincode,
            "phone": user.phone
        }
        return {"customer_details": customer_details}, 200

api.add_resource(CustomerDashboardAPI, '/api/customer/dashboard')


class SavePackageAPI(Resource):
    def get(self):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return {"message": "User not found"}, 404
        
        saved_packages = []
        for package_id in session['saved_packages']:
            package = ServicePackage.query.get(package_id)
            saved_packages.append({"id": package.id, "name": package.name, "description": package.description, "price": package.price})
        return {"saved_packages": saved_packages}, 200
    
    def post(self):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        data = request.get_json()
        package_id = data.get('package_id')
        
        if not package_id:
            return {"message": "Package ID is required"}, 400
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return {"message": "User not found"}, 404
        
        package = ServicePackage.query.get(package_id)
        
        if not package:
            return {"message": "Package not found"}, 404
        
        if package_id in session['saved_packages']:
            return {"message": "Package already saved"}, 400
        
        session['saved_packages'].append(package_id)
        return {"message": "Package saved successfully"}, 200

    def delete(self):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        data = request.get_json()
        package_id = data.get('package_id')
        
        if not package_id:
            return {"message": "Package ID is required"}, 400
        
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        
        if not user:
            return {"message": "User not found"}, 404
        
        if package_id not in session['saved_packages']:
            return {"message": "Package not saved"}, 400
        
        session['saved_packages'].remove(package_id)
        return {"message": "Package unsaved successfully"}, 200

api.add_resource(SavePackageAPI, '/api/customer/save_package')

# service packages 
class PackageAPI(Resource):
    def get(self):
        if not session.get('logged_in'):
            return {"message": "login to access"}, 403
        packages = ServicePackage.query.all()
        package_list = [
            {"id": p.id, "name": p.name, "service_id": p.service_id, "professional_id": p.professional_id, 
             "price": p.price, "duration": p.duration, "description": p.description}
            for p in packages
        ]
        return {"packages": package_list}, 200

api.add_resource(PackageAPI, '/api/packages')


class ServiceRequestAPI(Resource):
    def get(self, request_id=None):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        user_id = session.get('user_id')
        if request_id:
            service_request = ServiceRequest.query.filter_by(id=request_id, customer_id=user_id).first()
            if not service_request:
                return {"message": "Service request not found"}, 404
            return {"service_request": {
                "id": service_request.id,
                "package_id": service_request.package_id,
                "status": service_request.status,
                "created_at": str(service_request.date_of_request)
                
            }}, 200
        else:
            service_requests = ServiceRequest.query.filter_by(customer_id=user_id).all()
            requests_list = []
            for request in service_requests:
                requests_list.append({
                    "id": request.id,
                    "package_id": request.package_id,
                    "status": request.status,
                    "created_at": str(request.date_of_request),                    
                })
            return {"service_requests": requests_list}, 200

    def post(self):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        data = request.get_json()
        package_id = data.get('package_id')
        
        if not package_id:
            return {"message": "Package ID is required"}, 400
        
        user_id = session.get('user_id')
        new_request = ServiceRequest(
            user_id=user_id,
            package_id=package_id,
            status="pending"
        )
        db.session.add(new_request)
        db.session.commit()
        return {"message": "Service request created successfully"}, 201

    def put(self, request_id):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        data = request.get_json()
        status = data.get('status')
        
        if not status:
            return {"message": "Status is required"}, 400
        
        user_id = session.get('user_id')
        service_request = ServiceRequest.query.filter_by(id=request_id, user_id=user_id).first()
        
        if not service_request:
            return {"message": "Service request not found"}, 404
        
        service_request.status = status
        db.session.commit()
        return {"message": "Service request updated successfully"}, 200

    def delete(self, request_id):
        if not session.get('logged_in') or session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403
        
        user_id = session.get('user_id')
        service_request = ServiceRequest.query.filter_by(id=request_id, user_id=user_id).first()
        
        if not service_request:
            return {"message": "Service request not found"}, 404
        
        db.session.delete(service_request)
        db.session.commit()
        return {"message": "Service request deleted successfully"}, 200

api.add_resource(ServiceRequestAPI, '/api/customer/service_request', '/api/customer/service_request/<int:request_id>')

class AddReviewAPI(Resource):
    def post(self, request_id):
        if session.get('userole') != "customer":
            return {"message": "Permission denied"}, 403

        data = request.get_json()
        new_review = Review(
            service_request_id=request_id,
            rating=data['rating'],
            comment=data['comment']
        )
        db.session.add(new_review)
        db.session.commit()
        return {"message": "Review added successfully"}, 201

api.add_resource(AddReviewAPI, '/api/customer/service_request/<int:request_id>/review')

class ReviewsAPI(Resource):
    def get(self, package_id):
        if session.get('logged_in') != True:
            return {"message": "Authentication required"}, 401
        reviews = Review.query.filter_by(service_request_id=package_id).all()
        review_list = [{"rating": r.rating, "comment": r.comment, "date": str(r.date_created)} for r in reviews]
        return {"reviews": review_list}, 200

api.add_resource(ReviewsAPI, '/api/reviews/<int:package_id>')


# professional specififc 

class ProfessionalDashboardAPI(Resource):
    def get(self):
        if session.get('userole') != "professional":
            return {"message": "Permission denied"}, 403

        professional = Professional.query.filter_by(p_name=session['username']).first()
        if not professional:
            return {"message": "Professional not found"}, 404

        service_requests = ServiceRequest.query.filter_by(professional_id=professional.id).all()
        requests_list = []
        for request in service_requests:
            requests_list.append({
                "id": request.id,
                "package_id": request.package_id,
                "status": request.status,
                "created_at": str(request.date_of_request)
            })
        packages_list = ServicePackage.query.filter_by(professional_id=professional.id).all()
        pkg_list = []
        for package in packages_list:
            pkg_list.append({
                "id": package.id,
                "name": package.name,
                "price": package.price,
                "duration": package.duration,
                "description": package.description
            })
        return {"service_requests": requests_list, "My_packages" : pkg_list}, 200

api.add_resource(ProfessionalDashboardAPI, '/api/professional/dashboard')

class CreatePackageAPI(Resource):
    def post(self):
        if session.get('userole') != "professional":
            return {"message": "Permission denied"}, 403

        professional = Professional.query.filter_by(p_name=session['username']).first()
        if not professional:
            return {"message": "Professional not found"}, 404

        data = request.get_json()
        new_package = ServicePackage(
            professional_id=professional.id,
            service_id=data['service_id'],
            name=data['name'],
            price=data['price'],
            duration=data['duration'],
            description=data['description']
        )
        db.session.add(new_package)
        db.session.commit()
        return {"message": "Package created successfully"}, 201

api.add_resource(CreatePackageAPI, '/api/professional/package')

class UpdatePackageAPI(Resource):
    def put(self, package_id):
        if session.get('userole') != "professional":
            return {"message": "Permission denied"}, 403

        package = ServicePackage.query.get(package_id)
        if not package:
            return {"message": "Package not found"}, 404

        data = request.get_json()
        package.name = data.get('name', package.name)
        package.price = data.get('price', package.price)
        package.duration = data.get('duration', package.duration)
        package.description = data.get('description', package.description)
        db.session.commit()
        return {"message": "Package updated successfully"}, 200

api.add_resource(UpdatePackageAPI, '/api/professional/package/<int:package_id>')

class DeletePackageAPI(Resource):
    def delete(self, package_id):
        if session.get('userole') == "customer":
            return {"message": "Permission denied"}, 403

        package = ServicePackage.query.get(package_id)
        if not package:
            return {"message": "Package not found"}, 404

        db.session.delete(package)
        db.session.commit()
        return {"message": "Package deleted successfully"}, 200

api.add_resource(DeletePackageAPI, '/api/package/<int:package_id>')


class UpdateServiceRequestStatusAPI(Resource):
    def put(self, request_id):
        if session.get('userole') != "professional":
            return {"message": "Permission denied"}, 403

        data = request.get_json()
        new_status = data.get('status')

        service_request = ServiceRequest.query.get(request_id)
        if not service_request:
            return {"message": "Service request not found"}, 404

        service_request.status = new_status
        db.session.commit()
        return {"message": "Service request status updated successfully"}, 200

api.add_resource(UpdateServiceRequestStatusAPI, '/api/professional/service_request/<int:request_id>/status')



#admin specififc 
class ApproveProfessionalAPI(Resource):
    def put(self, professional_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403
        
        professional = Professional.query.get(professional_id)
        
        if not professional:
            return {"message": "Professional not found"}, 404
        
        professional.is_approved = True
        db.session.commit()
        return {"message": "Professional approved"}, 200

api.add_resource(ApproveProfessionalAPI, '/api/admin/approve_professional/<int:professional_id>')

class BlockProfessionalAPI(Resource):
    def put(self, professional_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        professional = Professional.query.get(professional_id)
        if not professional:
            return {"message": "Professional not found"}, 404

        try:
            db.session.query(Professional).filter(Professional.id == professional_id).update({
                Professional.is_blocked: True, Professional.is_approved: False
            })
            db.session.commit()
            return {"message": "Professional blocked successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"An error occurred: {str(e)}"}, 500
api.add_resource(BlockProfessionalAPI, '/api/admin/block_professional/<int:professional_id>')

class RejectProfessionalAPI(Resource):
    def delete(self, professional_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        professional = Professional.query.get(professional_id)
        if not professional:
            return {"message": "Professional not found"}, 404

        db.session.delete(professional)
        db.session.commit()
        return {"message": "Professional deleted successfully"}, 200

api.add_resource(RejectProfessionalAPI, '/api/admin/reject_professional/<int:professional_id>')


# block customers

class BlockCustAPI(Resource):
    def put(self, user_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        user = User.query.get(user_id)
        if not user:
            return {"message": "User not found"}, 404

        try:
            db.session.query(User).filter(User.id == user_id).update({
                User.is_blocked: True
            })
            db.session.commit()
            return {"message": "User blocked successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"An error occurred: {str(e)}"}, 500

api.add_resource(BlockCustAPI, '/api/admin/block_customer/<int:user_id>')

class UnBlockCustomerAPI(Resource):
    def put(self, user_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        user = User.query.get(user_id)
        if not user:
            return {"message": "User not found"}, 404

        try:
            db.session.query(User).filter(User.id == user_id).update({
                User.is_blocked: False
            })
            db.session.commit()
            return {"message": "User unblocked successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"An error occurred: {str(e)}"}, 500

api.add_resource(UnBlockCustomerAPI, '/api/admin/unblock_customer/<int:user_id>')

## services crud by admin and pro 
class ServiceAPI(Resource):
    
    def get(self):
        if session.get('logged_in') != True:
            return {"message": "Authentication required"}, 401
        services = Service.query.all()
        service_list = [{"id": s.id, "name": s.name, "category": s.category, "base_price": s.base_price, "description": s.description} for s in services]
        return {"services": service_list}, 200

    def post(self):
        
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        data = request.get_json()
        new_service = Service(
            name=data['name'],
            category=data['category'],
            base_price=data['base_price'],
            description=data['description']
        )
        db.session.add(new_service)
        db.session.commit()
        return {"message": "Service added successfully"}, 201


    def delete(self, service_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        service = Service.query.get(service_id)
        if not service:
            return {"message": "Service not found"}, 404

        db.session.delete(service)
        db.session.commit()
        return {"message": "Service deleted successfully"}, 200

    def put(self, service_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        service = Service.query.get(service_id)
        if not service:
            return {"message": "Service not found"}, 404

        data = request.get_json()
        service.name = data.get('name', service.name)
        service.category = data.get('category', service.category)
        service.base_price = data.get('base_price', service.base_price)
        service.description = data.get('description', service.description)
        db.session.commit()
        return {"message": "Service updated successfully"}, 200

api.add_resource(ServiceAPI, '/api/services', '/api/admin/services', '/api/admin/service/<int:service_id>')



class DashboardAPI(Resource):
    def get(self):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        total_users = User.query.filter_by(role='customer').count()
        plat_users = User.query.filter_by(type='Platinum').count()
        total_professionals = Professional.query.filter_by(is_approved=True).count()
        total_services = Service.query.count()
        total_service_requests = ServiceRequest.query.count()
        total_revenue = ServicePackage.query.with_entities(func.sum(ServicePackage.price)).scalar()
        completed_requests = ServiceRequest.query.filter_by(status='Completed').count()
        closed_requests = ServiceRequest.query.filter_by(status='Closed').count()
        pending_services = ServiceRequest.query.filter(or_(ServiceRequest.status == 'Requested', ServiceRequest.status == 'Accepted')).count()

        overall_ratings = db.session.query(Review.rating, func.count(Review.id)).group_by(Review.rating).all()
        ratings_data = {str(r[0]): r[1] for r in overall_ratings}

        ratings_by_service = db.session.query(ServicePackage.name, func.avg(Review.rating).label('avg_rating')).select_from(ServicePackage).join(ServiceRequest).join(Review).group_by(ServicePackage.name).all()
        pkg_data = {r[0]: r[1] for r in ratings_by_service}

        all_requests = db.session.query(ServiceRequest.status, func.count(ServiceRequest.id)).group_by(ServiceRequest.status).all()
        req_data = {r[0]: r[1] for r in all_requests}

        return {
            'total_users': total_users,
            'plat_users': plat_users,
            'total_professionals': total_professionals,
            'total_services': total_services,
            'total_service_requests': total_service_requests,
            'total_revenue': total_revenue,
            'completed_requests': completed_requests,
            'closed_requests': closed_requests,
            'pending_services': pending_services,
            'ratings_data': ratings_data,
            'pkg_data': pkg_data,
            'req_data': req_data
        }
api.add_resource(DashboardAPI, '/api/admin/dashboard')

class FlagPackageAPI(Resource):
    def post(self, package_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        package = ServicePackage.query.get(package_id)
        if not package:
            return {"message": "Package not found"}, 404

        try:
            db.session.query(ServicePackage).filter(ServicePackage.id == package_id).update({
                ServicePackage.is_flagged: True
            })
            db.session.commit()
            return {"message": "Package flagged successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"An error occurred: {str(e)}"}, 500

api.add_resource(FlagPackageAPI, '/api/admin/flag_package/<int:package_id>')

class UnFlagPackageAPI(Resource):
    def post(self, package_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403

        package = ServicePackage.query.get(package_id)
        if not package:
            return {"message": "Package not found"}, 404

        try:
            db.session.query(ServicePackage).filter(ServicePackage.id == package_id).update({
                ServicePackage.is_flagged: False
            })
            db.session.commit()
            return {"message": "Package unflagged successfully"}, 200
        except Exception as e:
            db.session.rollback()
            return {"message": f"An error occurred: {str(e)}"}, 500
        
api.add_resource(UnFlagPackageAPI, '/api/admin/unflag_package/<int:package_id>')


# profiles for customer and professionals

class ProfileAPI(Resource):
    def get(self, user_id=None):
        if not session.get('logged_in'):
            return {"message": "Authentication required"}, 401
        
        if session.get('userole') == "customer":
            user_id = session.get('user_id')
            user = User.query.get(user_id)
            if not user:
                return {"message": "User not found"}, 404
            
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "address": user.address,
                "pincode": user.pincode,
                "phone": user.phone
            }, 200
        elif session.get('userole') == "professional":
            professional = Professional.query.filter_by(p_name=session['username']).first()
            if not professional:
                return {"message": "Professional not found"}, 404
            
            return {
                "id": professional.id,
                "name": professional.p_name,
                "email": professional.p_email,
                "address": professional.paddress,
                "pincode": professional.p_pincode,
                "phone": professional.p_phone
            }, 200
        elif session.get('userole') == "admin":
            if not user_id:
                all_users = User.query.all()
                users_list = []
                for user in all_users:
                    users_list.append({"id": user.id,
                                       "username": user.username,
                                       "email": user.email,"blocked": user.is_blocked})
                all_professionals = Professional.query.all()
                professionals_list = []
                for professional in all_professionals:
                    professionals_list.append({"id": professional.id,
                                               "name": professional.p_name,
                                               "email": professional.p_email,
                                               "blocked": professional.is_blocked})
                return {"users": users_list, "professionals": professionals_list}, 200
            
            profile_page = User.query.get(user_id)
            return {
                "id": profile_page.id,
                "username": profile_page.username,
                "email": profile_page.email,
                "address": profile_page.address,
                "pincode": profile_page.pincode,
                "phone": profile_page.phone
            }, 200
            
api.add_resource(ProfileAPI, '/api/profile/<int:user_id>', '/api/profile')

# pro profile by admin 
class ProfessionalProfileAPI(Resource):
    def get(self, professional_id):
        if session.get('userole') != "admin":
            return {"message": "Permission denied"}, 403
        
        professional = Professional.query.get(professional_id)
        if not professional:
            return {"message": "Professional not found"}, 404
        
        return {
            "id": professional.id,
            "name": professional.p_name,
            "email": professional.p_email,
            "address": professional.paddress,
            "pincode": professional.p_pincode,
            "phone": professional.p_phone,
            "approved": professional.is_approved,
            "blocked": professional.is_blocked
            
        }, 200
api.add_resource(ProfessionalProfileAPI, '/api/admin/professional_profile/<int:professional_id>')
            
    
    
#swagger = Swagger(app)