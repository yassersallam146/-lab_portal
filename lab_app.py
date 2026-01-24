
import os
import secrets
import shutil
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import FastAPI, Request, Form, Depends, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, func, or_, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, validator
from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta

# حذف النتائج تلقائياً بعد 14 يوم (غير الرقم لو عايز شهر = 30)
RESULT_RETENTION_DAYS = 14

def cleanup_old_results():
    """حذف النتائج الأقدم من 14 يوم"""
    db = SessionLocal()
    try:
        cutoff_date = datetime.now() - timedelta(days=RESULT_RETENTION_DAYS)
        old_orders = db.query(TestOrder).filter(
            TestOrder.published == True,
            TestOrder.created_at < cutoff_date
        ).all()
        
        deleted_count = 0
        for order in old_orders:
            if order.result_file and os.path.exists(order.result_file):
                try:
                    os.remove(order.result_file)
                except:
                    pass
            order.result_file = None
            order.published = False
            deleted_count += 1
        
        db.commit()
        logger.info(f"تم حذف {deleted_count} نتيجة قديمة")
    except Exception as e:
        logger.error(f"خطأ في الحذف: {e}")
        db.rollback()
    finally:
        db.close()

# تشغيل الحذف التلقائي كل 24 ساعة
scheduler = BackgroundScheduler()
scheduler.add_job(cleanup_old_results, 'interval', hours=24)
scheduler.start()
# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

app = FastAPI(title="Laboratory Management System")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "Abqrino_Final_Pro_2026_CHANGE_ME"))

# Directory setup
UPLOAD_DIR = "results_files"
for folder in ["static", "templates", UPLOAD_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/results_files", StaticFiles(directory=UPLOAD_DIR), name="results_files")
templates = Jinja2Templates(directory="templates")

# Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
FAKE_PUBLISH_LINK = "https://lab-portal-8u49.onrender.com"  # Temporary fake link

# --- Database Models ---
Base = declarative_base()
engine = create_engine("sqlite:///lab.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    can_view_finance = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, index=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    address = Column(String, nullable=True)
    last_visit = Column(DateTime, default=datetime.now)
    notes = Column(Text, nullable=True)
    orders = relationship("TestOrder", back_populates="patient", order_by="desc(TestOrder.created_at)")

class TestOrder(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    patient_name = Column(String, nullable=False)
    test_name = Column(String, nullable=False)
    price = Column(Integer, nullable=False)
    pin = Column(String, unique=True, nullable=False, index=True)
    result_file = Column(String, nullable=True)
    published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    notes = Column(Text, nullable=True)
    patient = relationship("Patient", back_populates="orders")

class SystemSettings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    publish_link = Column(String, default=FAKE_PUBLISH_LINK)
    lab_name = Column(String, default="مختبر الطبي")
    updated_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

# --- Pydantic Models ---
class OrderCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    test: str
    price: int
    
    @validator('price')
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('السعر يجب أن يكون أكبر من صفر')
        return v
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('الاسم مطلوب')
        return v.strip()

# --- Dependencies ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def require_role(allowed_roles: list):
    def role_checker(request: Request):
        user = get_current_user(request)
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول")
        return user
    return role_checker

# --- Utility Functions ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_secure_pin() -> str:
    """Generate a secure 8-character PIN"""
    return secrets.token_urlsafe(6)[:8].upper()

def get_or_create_settings(db: Session) -> SystemSettings:
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

# --- Startup ---
@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        # Create default users with hashed passwords
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password=hash_password("admin123"),
                role="admin",
                can_view_finance=True
            )
            db.add(admin)
            logger.info("Created admin user")
        
        if not db.query(User).filter(User.username == "staff").first():
            staff = User(
                username="staff",
                password=hash_password("staff123"),
                role="employee",
                can_view_finance=False
            )
            db.add(staff)
            logger.info("Created staff user")
        
        # Create settings if not exist
        get_or_create_settings(db)
        
        db.commit()
    except Exception as e:
        logger.error(f"Startup error: {e}")
        db.rollback()
    finally:
        db.close()

# --- Authentication Routes ---
@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post('/login')
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(User).filter(User.username == username).first()
        
        if not user or not verify_password(password, user.password):
            logger.warning(f"Failed login attempt for username: {username}")
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "اسم المستخدم أو كلمة المرور غير صحيحة"
            })
        
        request.session["user"] = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "can_view_finance": user.can_view_finance
        }
        
        logger.info(f"User {username} logged in successfully")
        return RedirectResponse("/", status_code=303)
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "حدث خطأ أثناء تسجيل الدخول"
        })

@app.get('/logout')
def logout(request: Request):
    username = request.session.get("user", {}).get("username", "Unknown")
    request.session.clear()
    logger.info(f"User {username} logged out")
    return RedirectResponse("/login", status_code=303)

# --- Dashboard ---
@app.get('/', response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request)
        
        p_count = db.query(Patient).count()
        o_count = db.query(TestOrder).count()
        today_orders = db.query(TestOrder).filter(
            func.date(TestOrder.created_at) == date.today()
        ).count()
        
        pending_results = db.query(TestOrder).filter(
            TestOrder.published == False
        ).count()
        
        # Get employee for permission management (admin only)
        employee = None
        if user.get("role") == "admin":
            employee = db.query(User).filter(User.username == "staff").first()
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "patient_count": p_count,
            "order_count": o_count,
            "today_orders": today_orders,
            "pending_results": pending_results,
            "user": user,
            "employee": employee
        })
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Patient Management ---
@app.get('/patients', response_class=HTMLResponse)
def patients_page(
    request: Request,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        query = db.query(Patient)
        if search:
            query = query.filter(
                or_(
                    Patient.name.ilike(f"%{search}%"),
                    Patient.phone.ilike(f"%{search}%")
                )
            )
        
        patients = query.order_by(Patient.last_visit.desc()).all()
        
        return templates.TemplateResponse("patients.html", {
            "request": request,
            "patients": patients,
            "search": search or ""
        })
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.get('/patient_details/{patient_id}', response_class=HTMLResponse)
def patient_details(patient_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request)
        
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="المريض غير موجود")
        
        return templates.TemplateResponse("patient_history.html", {
            "request": request,
            "patient": patient
        })
    
    except HTTPException as he:
        if he.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

@app.get('/search_patients')
def search_patients(query: str, db: Session = Depends(get_db)):
    """Autocomplete endpoint for patient search"""
    try:
        patients = db.query(Patient).filter(
            or_(
                Patient.name.ilike(f"%{query}%"),
                Patient.phone.ilike(f"%{query}%")
            )
        ).limit(10).all()
        
        return [{"name": p.name, "phone": p.phone or ""} for p in patients]
    
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

# --- Order Management ---
@app.get('/orders', response_class=HTMLResponse)
def orders_page(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        query = db.query(TestOrder)
        
        if status == "pending":
            query = query.filter(TestOrder.published == False)
        elif status == "published":
            query = query.filter(TestOrder.published == True)
        
        orders = query.order_by(TestOrder.created_at.desc()).all()
        settings = get_or_create_settings(db)
        
        return templates.TemplateResponse("orders.html", {
            "request": request,
            "orders": orders,
            "status_filter": status,
            "publish_link": settings.publish_link
        })
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.get('/add_order', response_class=HTMLResponse)
def add_order_page(request: Request):
    try:
        user = get_current_user(request)
        return templates.TemplateResponse("add_order.html", {"request": request})
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.post('/add_order')
def add_order(
    request: Request,
    name: str = Form(...),
    phone: str = Form(None),
    test: str = Form(...),
    price: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        # Validate inputs
        order_data = OrderCreate(name=name, phone=phone, test=test, price=price)
        
        # Get or create patient
        patient = db.query(Patient).filter(Patient.name == order_data.name).first()
        if not patient:
            patient = Patient(name=order_data.name, phone=order_data.phone)
            db.add(patient)
            db.commit()
            db.refresh(patient)
        else:
            # Update patient's last visit
            patient.last_visit = datetime.now()
            if order_data.phone and not patient.phone:
                patient.phone = order_data.phone
        
        # Generate secure PIN
        pin = generate_secure_pin()
        while db.query(TestOrder).filter(TestOrder.pin == pin).first():
            pin = generate_secure_pin()
        
        # Create order
        new_order = TestOrder(
            patient_id=patient.id,
            patient_name=patient.name,
            test_name=order_data.test,
            price=order_data.price,
            pin=pin
        )
        db.add(new_order)
        db.commit()
        
        logger.info(f"Order created: {pin} for patient {patient.name}")
        
        return RedirectResponse('/orders', status_code=303)
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        logger.error(f"Add order error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء إضافة الطلب")

@app.post('/upload_result/{order_id}')
async def upload_result(
    order_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="الطلب غير موجود")
        
        # Validate file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"نوع الملف غير مسموح. الأنواع المسموحة: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read and validate file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="حجم الملف كبير جداً (الحد الأقصى 10 ميجابايت)")
        
        # Save file with secure name
        safe_filename = f"{order.pin}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Update order
        order.result_file = file_path
        order.published = True
        db.commit()
        
        logger.info(f"Result uploaded for order {order.pin}")
        
        return RedirectResponse('/orders', status_code=303)
    
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Upload error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="حدث خطأ أثناء رفع الملف")

# --- Finance ---
@app.get('/finance', response_class=HTMLResponse)
def finance_report(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        # Check finance permission
        if user.get("role") != "admin" and not user.get("can_view_finance"):
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول للحسابات")
        
        # Date filtering
        query = db.query(TestOrder)
        
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(TestOrder.created_at >= start)
        else:
            # Default to today
            query = query.filter(func.date(TestOrder.created_at) == date.today())
        
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(TestOrder.created_at <= end)
        
        orders = query.all()
        total = sum(o.price for o in orders)
        
        return templates.TemplateResponse("finance.html", {
            "request": request,
            "orders": orders,
            "total": total,
            "start_date": start_date or date.today().strftime('%Y-%m-%d'),
            "end_date": end_date or ""
        })
    
    except HTTPException as he:
        if he.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

# --- Settings & Admin ---
@app.post('/update_permission')
def update_permission(
    request: Request,
    finance_access: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية")
        
        staff = db.query(User).filter(User.username == "staff").first()
        if staff:
            staff.can_view_finance = finance_access is not None
            db.commit()
            logger.info(f"Staff finance permission updated: {staff.can_view_finance}")
        
        return RedirectResponse("/", status_code=303)
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.get('/settings', response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request)
        
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية")
        
        settings = get_or_create_settings(db)
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "settings": settings
        })
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.post('/update_settings')
def update_settings(
    request: Request,
    publish_link: str = Form(...),
    lab_name: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية")
        
        settings = get_or_create_settings(db)
        settings.publish_link = publish_link
        settings.lab_name = lab_name
        settings.updated_at = datetime.now()
        db.commit()
        
        logger.info("Settings updated")
        
        return RedirectResponse("/settings", status_code=303)
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

# --- Patient Portal (Public) ---
@app.get('/online_results', response_class=HTMLResponse)
def patient_portal(request: Request):
    return templates.TemplateResponse("patient_portal.html", {"request": request})

@app.post('/check_online')
def check_online(pin: str = Form(...), db: Session = Depends(get_db)):
    try:
        order = db.query(TestOrder).filter(
            TestOrder.pin == pin.strip().upper(),
            TestOrder.published == True
        ).first()
        
        if order:
            return JSONResponse({
                "status": "success",
                "patient": order.patient_name,
                "test": order.test_name,
                "file": f"/{order.result_file}",
                "date": order.created_at.strftime('%Y-%m-%d')
            })
        
        return JSONResponse({
            "status": "not_found",
            "message": "النتيجة غير موجودة أو لم يتم نشرها بعد"
        })
    
    except Exception as e:
        logger.error(f"Check online error: {e}")
        return JSONResponse({
            "status": "error",
            "message": "حدث خطأ أثناء البحث"
        })
    
# --- Profile Management (Corrected for FastAPI Dependency) ---
@app.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, db: Session = Depends(get_db)):
    # نحصل على بيانات المستخدم المسجل حالياً من الجلسة
    current_user_session = request.session.get("user")
    if not current_user_session:
        return RedirectResponse("/login", status_code=303)
    
    # جلب بيانات المستخدم من قاعدة البيانات باستخدام 'db' المحقونة
    user = db.query(User).filter(User.id == current_user_session["id"]).first()
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "title": "تعديل الحساب",
        "user": user
    })

@app.post("/profile")
async def update_profile(
    request: Request,
    username: str = Form(...),
    new_password: str = Form(None),
    current_password: str = Form(...),
    db: Session = Depends(get_db) # إضافة الـ Dependency هنا
):
    current_user_session = request.session.get("user")
    if not current_user_session:
        return RedirectResponse("/login", status_code=303)

    user = db.query(User).filter(User.id == current_user_session["id"]).first()

    # التحقق من كلمة المرور الحالية باستخدام الدالة المعرفة في كودك verify_password
    if not verify_password(current_password, user.password):
        return "كلمة المرور الحالية غير صحيحة!"

    # تحديث البيانات
    user.username = username
    if new_password and new_password.strip():
        user.password = hash_password(new_password) # استخدام دالة التشفير الموجودة في كودك
    
    try:
        db.commit()
        # تحديث بيانات الجلسة بالاسم الجديد
        request.session["user"]["username"] = username
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating profile: {e}")
        return "حدث خطأ أثناء حفظ التعديلات."

# هذا السطر يجب أن يكون في أول السطر تماماً (بدون مسافات)
if __name__ == "__main__":
    import uvicorn
    # هذه الأسطر يجب أن تكون محاذية لليمين (مسافة 4 فراغات)
    uvicorn.run(app, host="0.0.0.0", port=8000)
