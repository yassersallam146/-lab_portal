import os
import random
import shutil
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import FastAPI, Request, Form, Depends, File, UploadFile, HTTPException, Header, Response
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse # مجمعين هنا
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, func, or_, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

from starlette.middleware.sessions import SessionMiddleware
from passlib.context import CryptContext
from pydantic import BaseModel, validator
from apscheduler.schedulers.background import BackgroundScheduler

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

app = FastAPI(title="Laboratory Management System")
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "Abqrino_Final_Pro_2026_CHANGE_ME"))

# Directory setup
UPLOAD_DIR = "results_files"
LOGO_DIR = "static/images"
for folder in ["static", "templates", UPLOAD_DIR, LOGO_DIR]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get('/manifest.json')
def manifest():
    return JSONResponse(content={
        "name": "Lab Management System",
        "short_name": "Lab Portal",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#3498db",
        "icons": [
            {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ],
        "screenshots": [
            {
                "src": "/static/screenshot-mobile.png",
                "sizes": "1320x2321",
                "type": "image/png",
                "form_factor": "narrow",
                "label": "Lab Portal Mobile View"
            },
            {
                "src": "/static/screenshot-desktop.png",
                "sizes": "1888x861",
                "type": "image/png",
                "form_factor": "wide",
                "label": "Lab Portal Desktop View"
            }
        ]
    })

# لازم تضيف دول عشان السيرفر يرضى يبعت الصور للمتصفح
@app.get('/icon-192.png')
def icon192():
    return FileResponse('static/icon-192.png')

@app.get('/icon-512.png')
def icon512():
    return FileResponse('static/icon-512.png')

@app.get('/sw.js')
def service_worker():
    content = """
    self.addEventListener('install', (event) => {
        self.skipWaiting();
    });
    self.addEventListener('fetch', (event) => {
        event.respondWith(fetch(event.request));
    });
    """
    return Response(content=content, media_type='application/javascript')

app.mount("/results_files", StaticFiles(directory=UPLOAD_DIR), name="results_files")
templates = Jinja2Templates(directory="templates")

# Configuration
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
FAKE_PUBLISH_LINK = "https://yassersallam.pythonanywhere.com/api/upload"
RESULT_RETENTION_DAYS = 14

# --- نظام الترجمة ---
TRANSLATIONS = {
    "ar": {
        "dashboard": "لوحة التحكم",
        "patients": "المرضى",
        "orders": "الطلبات",
        "finance": "المالية",
        "settings": "الإعدادات",
        "logout": "تسجيل الخروج",
        "add_order": "إضافة طلب",
        "search": "بحث",
        "name": "الاسم",
        "phone": "الهاتف",
        "test": "التحليل",
        "price": "السعر",
        "actions": "الإجراءات",
        "pending": "قيد الانتظار",
        "published": "منشور",
        "view": "عرض",
        "edit": "تعديل",
        "delete": "حذف",
        "upload_result": "رفع النتيجة",
        "approve": "موافقة",
        "welcome": "مرحباً",
        "today_orders": "طلبات اليوم",
        "Register New Patient": "إضافة مريض جديد",
        "pending_results": "نتائج بانتظار النشر",
        "patient_count": "عدد المرضى",
        "order_count": "عدد الطلبات",
        "login": "تسجيل الدخول",
        "username": "اسم المستخدم",
        "password": "كلمة المرور",
        "submit": "إرسال",
        "back": "رجوع",
        "save": "حفظ",
        "cancel": "إلغاء",
        "error": "خطأ",
        "success": "تم بنجاح",
        "loading": "جاري التحميل...",
        "no_data": "لا توجد بيانات",
        "all_rights_reserved": "جميع الحقوق محفوظة",
        "search_patient": "بحث عن مريض...",
        "add_new_order": "إضافة طلب جديد",
        "patient_name": "اسم المريض",
        "patient_phone": "رقم الهاتف",
        "test_name": "اسم التحليل",
        "test_price": "سعر التحليل",
        "currency": "ج.م",
        "create_order": "إنشاء الطلب",
        "order_id": "رقم الطلب",
        "result": "النتيجة",
        "status": "الحالة",
        "date": "التاريخ",
        "options": "خيارات",
        "download": "تحميل",
        "approve_result": "الموافقة على النتيجة",
        "republish": "إعادة النشر",
        "lock": "قفل",
        "unlock": "فتح",
        "total": "الإجمالي",
        "report": "تقرير مالي",
        "from_date": "من تاريخ",
        "to_date": "إلى تاريخ",
        "generate_report": "إنشاء التقرير",
        "profile": "الملف الشخصي",
        "change_password": "تغيير كلمة المرور",
        "current_password": "كلمة المرور الحالية",
        "new_password": "كلمة المرور الجديدة",
        "confirm_password": "تأكيد كلمة المرور",
        "update": "تحديث",
        "online_results": "النتائج أونلاين",
        "enter_pin": "أدخل رقم PIN",
        "check_result": "التحقق من النتيجة",
        "result_not_found": "النتيجة غير موجودة أو لم يتم نشرها بعد",
        "search_error": "حدث خطأ أثناء البحث",
        "lab_name": "اسم المختبر",
        "publish_link": "رابط النشر",
        "default_language": "اللغة الافتراضية",
        "show_language": "إظهار خيار اللغة للمستخدمين",
        "update_settings": "تحديث الإعدادات",
        "admin": "مدير",
        "employee": "موظف",
        "view_finance": "عرض المالية",
        "update_permissions": "تحديث الصلاحيات",
        "patient_history": "سجل المريض",
        "age": "العمر",
        "gender": "الجنس",
        "address": "العنوان",
        "notes": "ملاحظات",
        "last_visit": "آخر زيارة",
        "edit_patient": "تعديل بيانات المريض",
        "delete_patient": "حذف المريض",
        "confirm_delete": "هل أنت متأكد من الحذف؟",
        "yes": "نعم",
        "no": "لا",
        "order_details": "تفاصيل الطلب",
        "patient_info": "معلومات المريض",
        "test_info": "معلومات التحليل",
        "financial_info": "معلومات مالية",
        "pin": "رقم PIN",
        "created_at": "تاريخ الإنشاء",
        "upload_file": "رفع ملف",
        "choose_file": "اختر ملف",
        "file_size_limit": "الحد الأقصى 10 ميجابايت",
        "allowed_formats": "الصيغ المسموحة: PDF, JPG, PNG, DOC, DOCX",
        "upload": "رفع",
        "pending_approval": "بانتظار الموافقة",
        "approved": "تمت الموافقة",
        "rejected": "مرفوض",
        "all": "الكل",
        "filter": "تصفية",
        "clear_filter": "مسح التصفية",
        "export": "تصدير",
        "Cancel and Go Back": "إلغاء والعودة",
        "Save Data": "حفظ البيانات",
        "print": "طباعة",
        "refresh": "تحديث",
        "home": "الرئيسية",
        "about": "حول",
        "contact": "اتصل بنا",
        "privacy": "الخصوصية",
        "terms": "الشروط",
        "help": "المساعدة",
        "language": "اللغة",
        "arabic": "العربية",
        "english": "الإنجليزية",
        "change_language": "تغيير اللغة",
        "theme": "المظهر",
        "dark": "داكن",
        "light": "فاتح",
        "system": "النظام",
        "notifications": "الإشعارات",
        "mark_all_read": "تحديد الكل كمقروء",
        "view_all": "عرض الكل",
        "messages": "الرسائل",
        "tasks": "المهام",
        "calendar": "التقويم",
        "reports": "التقارير",
        "analytics": "التحليلات",
        "users": "المستخدمين",
        "roles": "الأدوار",
        "permissions": "الصلاحيات",
        "logs": "السجلات",
        "backup": "النسخ الاحتياطي",
        "maintenance": "الصيانة",
        "version": "الإصدار",
        "check_updates": "التحقق من التحديثات",
        "documentation": "التوثيق",
        "support": "الدعم",
        "feedback": "التقييم",
        "logout_confirm": "هل أنت متأكد من تسجيل الخروج؟",
        "session_expired": "انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى",
        "server_error": "خطأ في الخادم",
        "not_found": "غير موجود",
        "forbidden": "غير مسموح",
        "unauthorized": "غير مصرح",
        "bad_request": "طلب خاطئ",
        "timeout": "انتهت المهلة",
        "network_error": "خطأ في الشبكة",
        "try_again": "حاول مرة أخرى",
        "contact_admin": "اتصل بالمدير",
        "go_back": "العودة",
        "continue": "المتابعة",
        "close": "إغلاق",
        "minimize": "تصغير",
        "maximize": "تكبير",
        "fullscreen": "ملء الشاشة",
        "exit_fullscreen": "الخروج من ملء الشاشة",
        "zoom_in": "تكبير",
        "zoom_out": "تصغير",
        "reset_zoom": "إعادة تعيين التكبير",
        "rotate": "تدوير",
        "crop": "قص",
        "undo": "تراجع",
        "redo": "إعادة",
        "cut": "قص",
        "copy": "نسخ",
        "paste": "لصق",
        "select_all": "تحديد الكل",
        "find": "بحث",
        "replace": "استبدال",
        "save_changes": "حفظ التغييرات",
        "discard_changes": "تجاهل التغييرات",
        "preview": "معاينة",
        "publish": "نشر",
        "unpublish": "إلغاء النشر",
        "archive": "أرشفة",
        "restore": "استعادة",
        "trash": "سلة المحذوفات",
        "empty_trash": "تفريغ سلة المحذوفات",
        "permanent_delete": "حذف نهائي",
        "move_to": "نقل إلى",
        "copy_to": "نسخ إلى",
        "male": "ذكر",
        "female": "أنثى",
        "rename": "إعادة تسمية",
        "duplicate": "نسخ",
        "share": "مشاركة",
        "embed": "تضمين",
        "export_as": "تصدير كـ",
        "import": "استيراد",
        "sync": "مزامنة",
        "validate": "تحقق",
        "optimize": "تحسين",
        "compress": "ضغط",
        "extract": "استخراج",
        "encrypt": "تشفير",
        "decrypt": "فك التشفير",
        "sign": "توقيع",
        "verify": "تحقق",
        "scan": "مسح",
        "clean": "تنظيف",
        "update_available": "تحديث متاح",
        "install_update": "تثبيت التحديث",
        "restart_required": "يتطلب إعادة التشغيل",
        "changelog": "سجل التغييرات",
        "license": "الترخيص",
        "credits": "الاعتمادات",
        "acknowledgments": "شكر وتقدير",
        "copyright": "حقوق النشر",
        "trademark": "العلامة التجارية",
        "patent": "براءة الاختراع",
        "disclaimer": "إخلاء المسؤولية",
        "warranty": "الضمان",
        "liability": "المسؤولية",
        "indemnity": "التعويض",
        "governance": "الحوكمة",
        "compliance": "الامتثال",
        "security": "الأمان",
        "privacy_policy": "سياسة الخصوصية",
        "terms_of_service": "شروط الخدمة",
        "acceptable_use": "الاستخدام المقبول",
        "code_of_conduct": "قواعد السلوك",
        "ethics": "الأخلاقيات",
        "values": "القيم",
        "mission": "المهمة",
        "vision": "الرؤية",
        "strategy": "الاستراتيجية",
        "objectives": "الأهداف",
        "milestones": "المعالم",
        "timeline": "الجدول الزمني",
        "roadmap": "خارطة الطريق",
        "blog": "المدونة",
        "news": "الأخبار",
        "events": "الفعاليات",
        "webinars": "الندوات عبر الإنترنت",
        "tutorials": "الدروس",
        "guides": "الإرشادات",
        "faq": "الأسئلة الشائعة",
        "forum": "المنتدى",
        "community": "المجتمع",
        "social_media": "وسائل التواصل الاجتماعي",
        "newsletter": "النشرة الإخبارية",
        "subscribe": "اشتراك",
        "unsubscribe": "إلغاء الاشتراك",
        "preferences": "التفضيلات",
        "account": "الحساب",
        "billing": "الفواتير",
        "payment": "الدفع",
        "invoice": "الفاتورة",
        "receipt": "الإيصال",
        "refund": "استرداد",
        "tax": "الضريبة",
        "discount": "الخصم",
        "coupon": "الكوبون",
        "voucher": "القسيمة",
        "credit": "الائتمان",
        "debit": "الدين",
        "balance": "الرصيد",
        "transaction": "المعاملة",
        "statement": "كشف الحساب",
        "overview": "نظرة عامة",
        "details": "تفاصيل",
        "summary": "ملخص",
        "statistics": "إحصائيات",
        "metrics": "المقاييس",
        "kpi": "مؤشرات الأداء الرئيسية",
        "alerts": "التنبيهات",
        "monitoring": "المراقبة",
        "audit": "التدقيق",
        "inspection": "التفتيش",
        "certification": "الشهادة",
        "accreditation": "الاعتماد",
        "standard": "المعيار",
        "protocol": "البروتوكول",
        "procedure": "الإجراء",
        "workflow": "سير العمل",
        "pipeline": "خط الأنابيب",
        "queue": "قائمة الانتظار",
        "stack": "المكدس",
        "heap": "الكومة",
        "cache": "ذاكرة التخزين المؤقت",
        "buffer": "المخزن المؤقت",
        "registry": "السجل",
        "repository": "المستودع",
        "archive": "الأرشيف",
        "recovery": "الاسترداد",
        "migration": "الهجرة",
        "upgrade": "الترقية",
        "downgrade": "التخفيض",
        "rollback": "التراجع",
        "patch": "الترقيع",
        "hotfix": "الإصلاح العاجل",
        "release": "الإصدار",
        "build": "البناء",
        "deploy": "النشر",
        "host": "المضيف",
        "domain": "النطاق",
        "server": "الخادم",
        "client": "العميل",
        "api": "واجهة برمجة التطبيقات",
        "sdk": "مجموعة تطوير البرمجيات",
        "library": "المكتبة",
        "framework": "الإطار",
        "platform": "المنصة",
        "infrastructure": "البنية التحتية",
        "cloud": "السحابة",
        "edge": "الحافة",
        "iot": "إنترنت الأشياء",
        "ai": "الذكاء الاصطناعي",
        "ml": "التعلم الآلي",
        "dl": "التعلم العميق",
        "nlp": "معالجة اللغة الطبيعية",
        "cv": "رؤية الكمبيوتر",
        "ar": "الواقع المعزز",
        "vr": "الواقع الافتراضي",
        "blockchain": "سلاسل الكتل",
        "crypto": "التشفير",
        "nft": "الرموز غير القابلة للاستبدال",
        "metaverse": "الكون الافتراضي",
        "web3": "الويب 3",
        "dao": "المنظمة اللامركزية المستقلة",
        "defi": "التمويل اللامركزي",
        "gamefi": "ألعاب التمويل",
        "socialfi": "التمويل الاجتماعي",
        "learnfi": "تعليم التمويل",
        "healthfi": "تمويل الصحة",
        "govfi": "تمويل الحوكمة",
        "regfi": "تمويل التنظيم",
        "legaltech": "التكنولوجيا القانونية",
        "fintech": "التكنولوجيا المالية",
        "edtech": "تكنولوجيا التعليم",
        "healthtech": "تكنولوجيا الصحة",
        "agritech": "تكنولوجيا الزراعة",
        "cleantech": "التكنولوجيا النظيفة",
        "greentech": "التكنولوجيا الخضراء",
        "spacetech": "تكنولوجيا الفضاء",
        "oceantech": "تكنولوجيا المحيطات",
        "biotech": "التكنولوجيا الحيوية",
        "nanotech": "تكنولوجيا النانو",
        "quantum": "الكم",
        "fusion": "الاندماج",
        "fission": "الانشطار",
        "renewable": "المتجددة",
        "sustainable": "المستدام",
        "circular": "الدائرية",
        "regenerative": "التجديدية",
        "restorative": "الترميمية",
        "conservation": "الحفظ",
        "preservation": "الحفظ",
        "restoration": "الترميم",
        "remediation": "الإصلاح",
        "rehabilitation": "إعادة التأهيل",
        "reconstruction": "إعادة الإعمار",
        "redevelopment": "إعادة التطوير",
        "revitalization": "إحياء",
        "renaissance": "نهضة",
        "revolution": "ثورة",
        "evolution": "تطور",
        "innovation": "ابتكار",
        "invention": "اختراع",
        "discovery": "اكتشاف",
        "exploration": "استكشاف",
        "research": "بحث",
        "development": "تطوير",
        "engineering": "هندسة",
        "science": "علم",
        "technology": "تكنولوجيا",
        "mathematics": "رياضيات",
        "physics": "فيزياء",
        "chemistry": "كيمياء",
        "biology": "أحياء",
        "geology": "جيولوجيا",
        "astronomy": "فلك",
        "meteorology": "الأرصاد الجوية",
        "oceanography": "علوم المحيطات",
        "seismology": "علم الزلازل",
        "volcanology": "علم البراكين",
        "paleontology": "علم الأحافير",
        "archaeology": "علم الآثار",
        "anthropology": "أنثروبولوجيا",
        "sociology": "علم الاجتماع",
        "psychology": "علم النفس",
        "philosophy": "فلسفة",
        "theology": "لاهوت",
        "history": "تاريخ",
        "geography": "جغرافيا",
        "economics": "اقتصاد",
        "politics": "سياسة",
        "law": "قانون",
        "medicine": "طب",
        "nursing": "تمريض",
        "pharmacy": "صيدلة",
        "dentistry": "طب الأسنان",
        "veterinary": "طب بيطري",
        "agriculture": "زراعة",
        "forestry": "حراجة",
        "fisheries": "مصايد الأسماك",
        "mining": "تعدين",
        "manufacturing": "تصنيع",
        "construction": "بناء",
        "transportation": "نقل",
        "communication": "اتصال",
        "energy": "طاقة",
        "water": "ماء",
        "waste": "نفايات",
        "environment": "بيئة",
        "climate": "مناخ",
        "weather": "طقس",
        "air": "هواء",
        "soil": "تربة",
        "biodiversity": "تنوع حيوي",
        "ecosystem": "نظام بيئي",
        "habitat": "موطن",
        "species": "نوع",
        "genus": "جنس",
        "family": "عائلة",
        "order": "رتبة",
        "class": "طائفة",
        "phylum": "شعبة",
        "kingdom": "مملكة",
        "domain": "نطاق",
        "life": "حياة",
        "universe": "كون",
        "galaxy": "مجرة",
        "star": "نجم",
        "planet": "كوكب",
        "moon": "قمر",
        "asteroid": "كويكب",
        "comet": "مذنب",
        "nebula": "سديم",
        "black_hole": "ثقب أسود",
        "wormhole": "ثقب دودي",
        "multiverse": "أكوان متعددة",
        "dimension": "بعد",
        "time": "زمن",
        "space": "فضاء",
        "matter": "مادة",
        "energy": "طاقة",
        "force": "قوة",
        "field": "حقل",
        "particle": "جسيم",
        "wave": "موجة",
        "quantum": "كم",
        "relativity": "نسبية",
        "gravity": "جاذبية",
        "electromagnetism": "كهرومغناطيسية",
        "strong_force": "قوة نووية شديدة",
        "weak_force": "قوة نووية ضعيفة",
        "standard_model": "النموذج القياسي",
        "string_theory": "نظرية الأوتار",
        "m_theory": "نظرية إم",
        "loop_quantum_gravity": "جاذبية كمية حلقية",
        "causal_dynamical_triangulation": "تثليث ديناميكي سببي",
        "asymptotic_safety": "سلامة مقاربية",
        "holographic_principle": "مبدأ الهولوغرام",
        "cosmic_censorship": "الرقابة الكونية",
        "chronology_protection": "حماية التسلسل الزمني",
        "anthropic_principle": "المبدأ الأنثروبي",
        "fine_tuning": "ضبط دقيق",
        "simulation_hypothesis": "فرضية المحاكاة",
        "panspermia": "تبزر الشامل",
        "abiogenesis": "نشأة الحياة من غير حياة",
        "genetic_drift": "انحراف وراثي",
        "gene_flow": "تدفق الجينات",
        "mutation": "طفرة",
        "speciation": "تكوين الأنواع",
        "extinction": "انقراض",
        "ecology": "علم البيئة",
        "resilience": "مرونة",
        "adaptation": "تكيف",
        "mitigation": "تخفيف",
        "reclamation": "استصلاح",
        "reforestation": "إعادة تشجير",
        "afforestation": "تشجير",
        "desertification": "تصحر",
        "deforestation": "إزالة الغابات",
        "soil_erosion": "تآكل التربة",
        "water_scarcity": "ندرة المياه",
        "air_pollution": "تلوث الهواء",
        "water_pollution": "تلوث المياه",
        "soil_pollution": "تلوث التربة",
        "noise_pollution": "تلوث ضوضائي",
        "light_pollution": "تلوث ضوئي",
        "thermal_pollution": "تلوث حراري",
        "radioactive_pollution": "تلوث إشعاعي",
        "plastic_pollution": "تلوث بلاستيكي",
        "microplastic": "لدائن دقيقة",
        "nanoplastic": "لدائن نانوية",
        "greenhouse_gas": "غازات دفيئة",
        "register_new_patient": "تسجيل مريض جديد",
        "name_placeholder": "أدخل الاسم كاملاً",
        "optional": "اختياري",
        "notes_placeholder": "أي ملاحظات إضافية هنا...",
        "save_data": "حفظ البيانات",
        "cancel_and_back": "إلغاء والعودة",
        "carbon_footprint": "بصمة كربونية",
        "carbon_offset": "تعويض كربوني",
        "carbon_credit": "رصيد كربوني",
        "carbon_tax": "ضريبة كربون",
        "emissions_trading": "تداول الانبعاثات",
        "cap_and_trade": "الحد والتجارة",
        "renewable_energy": "طاقة متجددة",
        "solar_energy": "طاقة شمسية",
        "wind_energy": "طاقة رياح",
        "hydroelectric": "طاقة كهرومائية",
        "geothermal": "طاقة حرارية أرضية",
        "tidal_energy": "طاقة المد والجزر",
        "wave_energy": "طاقة الأمواج",
        "bioenergy": "طاقة حيوية",
        "hydrogen": "هيدروجين",
        "nuclear": "نووي",
        "thorium": "ثوريوم",
        "uranium": "يورانيوم",
        "plutonium": "بلوتونيوم",
        "deuterium": "ديوتيريوم",
        "tritium": "تريتيوم",
        "helium": "هيليوم",
        "lithium": "ليثيوم",
        "cobalt": "كوبالت",
        "nickel": "نيكل",
        "copper": "نحاس",
        "zinc": "زنك",
        "silver": "فضة",
        "gold": "ذهب",
        "platinum": "بلاتين",
        "palladium": "بالاديوم",
        "rhodium": "روديوم",
        "iridium": "إيريديوم",
        "osmium": "أوزميوم",
        "ruthenium": "روثينيوم",
        "rhenium": "رينيوم",
        "tungsten": "تنغستن",
        "molybdenum": "موليبدينوم",
        "tantalum": "تانتالوم",
        "niobium": "نيوبيوم",
        "hafnium": "هافنيوم",
        "zirconium": "زركونيوم",
        "yttrium": "إتريوم",
        "lanthanum": "لانثانوم",
        "cerium": "سيريوم",
        "praseodymium": "براسيوديميوم",
        "neodymium": "نيوديميوم",
        "promethium": "بروميثيوم",
        "samarium": "ساماريوم",
        "europium": "يوروبيوم",
        "gadolinium": "جادولينيوم",
        "terbium": "تيربيوم",
        "dysprosium": "ديسبروسيوم",
        "holmium": "هولميوم",
        "erbium": "إربيوم",
        "thulium": "ثوليوم",
        "ytterbium": "إتيربيوم",
        "lutetium": "لوتيتيوم",
        "scandium": "سكانديوم",
        "titanium": "تيتانيوم",
        "vanadium": "فاناديوم",
        "chromium": "كروم",
        "manganese": "منغنيز",
        "iron": "حديد",
        "gallium": "غاليوم",
        "germanium": "جرمانيوم",
        "arsenic": "زرنيخ",
        "selenium": "سيلينيوم",
        "bromine": "بروم",
        "krypton": "كريبتون",
        "rubidium": "روبيديوم",
        "strontium": "سترونشيوم",
        "technetium": "تكنيشيوم",
        "cadmium": "كادميوم",
        "indium": "إنديوم",
        "tin": "قصدير",
        "antimony": "إثمد",
        "tellurium": "تيلوريوم",
        "iodine": "يود",
        "xenon": "زينون",
        "cesium": "سيزيوم",
        "barium": "باريوم",
        "protactinium": "بروتكتينيوم",
        "neptunium": "نبتونيوم",
        "americium": "أمريكيوم",
        "curium": "كوريوم",
        "berkelium": "بركليوم",
        "californium": "كاليفورنيوم",
        "einsteinium": "أينشتاينيوم",
        "fermium": "فيرميوم",
        "mendelevium": "مندليفيوم",
        "nobelium": "نوبليوم",
        "lawrencium": "لورنسيوم",
        "rutherfordium": "رذرفورديوم",
        "dubnium": "دوبنيوم",
        "seaborgium": "سيبورغيوم",
        "bohrium": "بوريوم",
        "hassium": "هسيوم",
        "meitnerium": "مايتنريوم",
        "darmstadtium": "دارمشتاتيوم",
        "roentgenium": "رونتجينيوم",
        "copernicium": "كوبرنيسيوم",
        "nihonium": "نيهونيوم",
        "flerovium": "فليروفيوم",
        "moscovium": "موسكوفيوم",
        "livermorium": "ليفرموريوم",
        "tennessine": "تينيسين",
        "oganesson": "أوغانيسون",
        # مفاتيح جديدة من القوالب
        "quick_actions": "إجراءات سريعة",
        "patient_list": "قائمة المرضى",
        "portal": "البوابة",
        "staff_perms": "صلاحيات الموظفين",
        "view_finance": "عرض المالية",
        "general_settings": "الإعدادات العامة",
        "permissions_and_language": "صلاحيات وظهور اللغة",
        "last_update": "آخر تحديث",
        "orders_list": "قائمة طلبات التحاليل",
        "pending_approval": "بانتظار الموافقة",
        "copy": "نسخ",
        "ready_to_publish": "جاهزة للنشر",
        "waiting_approval": "بانتظار الاعتماد",
        "in_lab": "قيد المختبر",
        "view_file": "عرض الملف",
        "copied": "تم النسخ بنجاح",
        "new_order_registration": "تسجيل طلب تحليل جديد",
        "patient_name_or_phone": "اسم المريض أو الهاتف",
        "search_patient_placeholder": "ابحث عن مريض موجود أو أضف جديد",
        "start_typing_to_search": "ابدأ بالكتابة للبحث عن مريض موجود",
        "phone_help": "رقم الجوال (10-11 رقم)",
        "test_example": "مثال: CBC - تحليل صورة دم كاملة",
        "save_order": "حفظ الطلب",
        "no_results_add_new": "لا توجد نتائج - سيتم إضافة مريض جديد",
        "cbc_test": "تحليل صورة دم كاملة",
        "fasting_sugar": "سكر صائم",
        "postprandial_sugar": "سكر فاطر",
        "liver_function": "وظائف كبد",
        "kidney_function": "وظائف كلى",
        "lipid_profile": "دهون",
        "vitamin_d": "فيتامين D",
        "tsh": "غدة درقية TSH",
        "lab_management_system": "نظام إدارة المختبر",
        "test_credentials": "معلومات تجريبية",
        "patient_record": "سجل المرضى",
        "full_list": "القائمة الكاملة",
        "patient": "مريض",
        "not_available": "غير متوفر",
        "view_history": "عرض السجل",
        "total_orders": "إجمالي الطلبات",
        "ready_results": "النتائج الجاهزة",
        "visit_and_test_history": "سجل الزيارات والتحاليل",
        "ready": "جاهزة",
        "in_process": "قيد المعالجة",
        "no_visits_registered": "لا توجد زيارات مسجلة",
        "back_to_patients": "الرجوع لقائمة المرضى",
        "patient_portal": "بوابة المرضى",
        "result_inquiry": "استعلام عن نتائج التحاليل الطبية",
        "enter_your_pin": "أدخل رقم الـ PIN الخاص بك",
        "pin_help": "الرقم السري الموجود في إيصالك",
        "pin_placeholder": "XXXXXXXX",
        "search_for_result": "البحث عن النتيجة",
        "searching": "جاري البحث...",
        "your_result_ready": "نتيجتك جاهزة!",
        "test_date": "تاريخ التحليل",
        "note_text": "يرجى مراجعة طبيبك المختص لفهم النتائج بشكل صحيح",
        "ensure": "تأكد من",
        "ensure_list1": "إدخال رقم الـ PIN بشكل صحيح",
        "ensure_list2": "أن النتيجة قد تم نشرها من قبل المختبر",
        "sorry": "عذراً",
        "current_username": "اسم المستخدم الحالي",
        "new_password_optional": "كلمة سر جديدة (اتركها فارغة إذا لا تريد التغيير)",
        "update_success": "تم تحديث البيانات بنجاح",
        "username_taken": "اسم المستخدم هذا مستخدم من قبل",
        "revenue_review": "مراجعة الإيرادات والحسابات",
        "filter_by_date": "تصفية حسب التاريخ",
        "total_revenue": "إجمالي الإيرادات",
        "invoice_count": "عدد الفواتير",
        "average_invoice": "متوسط الفاتورة",
        "transaction_details": "تفاصيل المعاملات",
        "amount": "المبلغ",
        "no_transactions": "لا توجد معاملات في هذه الفترة",
        "enter_pin_label": "الرقم السري للتقرير (PIN)",
        "enter_phone_or_name": "رقم الهاتف أو اسم المريض",
        "phone_or_name_placeholder": "أدخل رقم الهاتف المسجل لدينا",
        "enter_phone_or_name_error": "يرجى إدخال رقم الهاتف أو الاسم للتحقق",
        "ensure_list1": "التأكد من كتابة الرقم السري (PIN) بشكل صحيح.",
        "ensure_list2": "التأكد من إدخال رقم الهاتف الذي زودتنا به عند التسجيل.",
        "print_report": "طباعة التقرير",
    },
    "en": {
        # English translations (simplified version with only essential keys)
        "dashboard": "Dashboard",
        "patients": "Patients",
        "orders": "Orders",
        "finance": "Finance",
        "settings": "Settings",
        "logout": "Logout",
        "add_order": "Add Order",
        "search": "Search",
        "name": "Name",
        "phone": "Phone",
        "test": "Test",
        "price": "Price",
        "actions": "Actions",
        "pending": "Pending",
        "published": "Published",
        "view": "View",
        "edit": "Edit",
        "delete": "Delete",
        "upload_result": "Upload Result",
        "approve": "Approve",
        "welcome": "Welcome",
        "today_orders": "Today's Orders",
        "pending_results": "Pending Results",
        "patient_count": "Patient Count",
        "order_count": "Order Count",
        "login": "Login",
        "username": "Username",
        "password": "Password",
        "submit": "Submit",
        "back": "Back",
        "save": "Save",
        "cancel": "Cancel",
        "error": "Error",
        "success": "Success",
        "loading": "Loading...",
        "no_data": "No Data",
        "all_rights_reserved": "All Rights Reserved",
        "search_patient": "Search patient...",
        "patient_name": "Patient Name",
        "currency": "EGP",
        "status": "Status",
        "date": "Date",
        "download": "Download",
        "total": "Total",
        "from_date": "From Date",
        "to_date": "To Date",
        "profile": "Profile",
        "enter_pin": "Enter PIN",
        "check_result": "Check Result",
        "result_not_found": "Result not found or not published yet",
        "search_error": "An error occurred while searching",
        "lab_name": "Lab Name",
        "publish_link": "Publish Link",
        "default_language": "Default Language",
        "show_language": "Show language option to users",
        "admin": "Admin",
        "employee": "Employee",
        "patient_history": "Patient History",
        "age": "Age",
        "gender": "Gender",
        "male": "male",
        "female": "female",
        "address": "Address",
        "notes": "Notes",
        "last_visit": "Last Visit",
        "pin": "PIN",
        "created_at": "Created At",
        "upload_file": "Upload File",
        "all": "All",
        "filter": "Filter",
        "home": "Home",
        "language": "Language",
        "arabic": "Arabic",
        "english": "English",
        "change_language": "Change Language",
        # مفاتيح جديدة من القوالب
        "quick_actions": "Quick Actions",
        "patient_list": "Patient List",
        "portal": "Portal",
        "staff_perms": "Staff Permissions",
        "view_finance": "View Finance",
        "general_settings": "General Settings",
        "permissions_and_language": "Permissions and Language",
        "last_update": "Last Update",
        "save_changes": "Save Changes",
        "Save Data": "Save Data",
        "orders_list": "Orders List",
        "pending_approval": "Pending Approval",
        "copy": "Copy",
        "patient_name": "Patient Name",
        "test_name": "Test Name",
        "Register New Patient": "Register New Patient",
        "Cancel and Go Back": "Cancel and Go Back",
        "ready_to_publish": "Ready to Publish",
        "waiting_approval": "Waiting Approval",
        "in_lab": "In Lab",
        "view_file": "View File",
        "approve_result": "Approve Result",
        "copied": "Copied successfully",
        "new_order_registration": "New Test Order Registration",
        "patient_name_or_phone": "Patient Name or Phone",
        "search_patient_placeholder": "Search for existing patient or add new",
        "start_typing_to_search": "Start typing to search for an existing patient",
        "phone_help": "Mobile number (10-11 digits)",
        "test_example": "Example: CBC - Complete Blood Count",
        "save_order": "Save Order",
        "no_results_add_new": "No results - a new patient will be added",
        "cbc_test": "Complete Blood Count",
        "fasting_sugar": "Fasting Blood Sugar",
        "postprandial_sugar": "Postprandial Blood Sugar",
        "liver_function": "Liver Function Tests",
        "kidney_function": "Kidney Function Tests",
        "lipid_profile": "Lipid Profile",
        "vitamin_d": "Vitamin D",
        "tsh": "Thyroid TSH",
        "lab_management_system": "Laboratory Management System",
        "test_credentials": "Test Credentials",
        "patient_record": "Patient Record",
        "full_list": "Full List",
        "patient": "patient",
        "not_available": "Not Available",
        "view_history": "View History",
        "total_orders": "Total Orders",
        "ready_results": "Ready Results",
        "visit_and_test_history": "Visit and Test History",
        "ready": "Ready",
        "in_process": "In Process",
        "no_visits_registered": "No visits registered",
        "back_to_patients": "Back to Patients List",
        "patient_portal": "Patient Portal",
        "result_inquiry": "Medical Test Results Inquiry",
        "enter_your_pin": "Enter your PIN number",
        "pin_help": "The secret number on your receipt",
        "pin_placeholder": "XXXXXXXX",
        "search_for_result": "Search for Result",
        "searching": "Searching...",
        "enter_pin": "Please enter PIN number",
        "your_result_ready": "Your result is ready!",
        "test_date": "Test Date",
        "note": "Note",
        "note_text": "Please consult your specialist doctor to understand the results correctly",
        "ensure": "Make sure",
        "ensure_list1": "Enter the PIN correctly",
        "ensure_list2": "The result has been published by the laboratory",
        "sorry": "Sorry",
        "current_username": "Current Username",
        "new_password_optional": "New password (leave blank if you don't want to change)",
        "update_success": "Data updated successfully",
        "username_taken": "This username is already taken",
        "revenue_review": "Revenue and Accounts Review",
        "filter_by_date": "Filter by Date",
        "total_revenue": "Total Revenue",
        "invoice_count": "Invoice Count",
        "average_invoice": "Average Invoice",
        "transaction_details": "Transaction Details",
        "amount": "Amount",
        "register_new_patient": "Register New Patient",
        "name_placeholder": "Enter full name",
        "optional": "Optional",
        "notes_placeholder": "Any extra notes here...",
        "save_data": "Save Data",
        "cancel_and_back": "Cancel and Go Back",
        "no_transactions": "No transactions in this period",
        "enter_pin_label": "Report PIN Code",
        "enter_phone_or_name": "Phone Number or Patient Name",
        "phone_or_name_placeholder": "Enter your registered phone number",
        "enter_phone_or_name_error": "Please enter phone number or name to verify",
        "ensure_list1": "Make sure the PIN code is entered correctly.",
        "ensure_list2": "Make sure to enter the phone number you provided us.",
        "print_report": "Print Report",
    }
}

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
    preferred_language = Column(String, default="ar")
    created_at = Column(DateTime, default=datetime.now)

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True, nullable=False)
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
    currency = Column(String, default="ج.م")
    pin = Column(String, unique=True, nullable=False, index=True)
    result_file = Column(String, nullable=True)
    published = Column(Boolean, default=False)
    admin_approved = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    notes = Column(Text, nullable=True)
    patient = relationship("Patient", back_populates="orders")

class SystemSettings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    publish_link = Column(String, default=FAKE_PUBLISH_LINK)
    lab_name = Column(String, default="مختبر الطبي")
    logo_path = Column(String, default="/static/images/logo.png")
    default_language = Column(String, default="ar")
    updated_at = Column(DateTime, default=datetime.now)
    show_language_to_users = Column(Boolean, default=False)
    show_finance_to_users = Column(Boolean, default=False)

Base.metadata.create_all(bind=engine)

# --- Pydantic Models ---
class OrderCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    test: str
    price: int
    currency: Optional[str] = "ج.م"
    
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

def require_admin(request: Request):
    user = get_current_user(request)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

# --- Utility Functions ---
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_secure_pin(phone: str = None) -> str:
    """Generate 6-digit PIN: last 2 digits of phone + 4 random digits"""
    if phone and len(phone) >= 2:
        last_two = phone[-2:]
    else:
        last_two = f"{random.randint(10, 99)}"
    
    random_four = f"{random.randint(1000, 9999)}"
    return last_two + random_four

def get_or_create_settings(db: Session) -> SystemSettings:
    settings = db.query(SystemSettings).first()
    if not settings:
        settings = SystemSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings

def get_language(request: Request, db: Session = None):
    """الحصول على لغة المستخدم الحالي"""
    user_session = request.session.get("user")
    
    if user_session and user_session.get("language"):
        return user_session.get("language")
    
    # إذا لم يكن هناك مستخدم مسجل، استخدم اللغة الافتراضية من الإعدادات
    if db:
        settings = get_or_create_settings(db)
        return settings.default_language
    
    return "ar"

def get_translations(request: Request, db: Session = None):
    """الحصول على النصوص المترجمة للغة الحالية"""
    lang = get_language(request, db)
    return TRANSLATIONS.get(lang, TRANSLATIONS["ar"])

def cleanup_old_results():
    """حذف النتائج الأقدم من RESULT_RETENTION_DAYS يوم"""
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

# --- Startup ---
@app.on_event("startup")
def startup():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password=hash_password("admin123"),
                role="admin",
                can_view_finance=True,
                preferred_language="ar"
            )
            db.add(admin)
            logger.info("Created admin user")
        
        if not db.query(User).filter(User.username == "staff").first():
            staff = User(
                username="staff",
                password=hash_password("staff123"),
                role="employee",
                can_view_finance=False,
                preferred_language="ar"
            )
            db.add(staff)
            logger.info("Created staff user")
        
        get_or_create_settings(db)
        db.commit()
    except Exception as e:
        logger.error(f"Startup error: {e}")
        db.rollback()
    finally:
        db.close()

# --- Authentication Routes ---
@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if request.session.get("user"):
        return RedirectResponse("/", status_code=303)
    
    lang = get_language(request, db)
    translations = get_translations(request, db)
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": None,
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
        "t": translations
    })

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
            
            lang = get_language(request, db)
            translations = get_translations(request, db)
            
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "اسم المستخدم أو كلمة المرور غير صحيحة",
                "lang": lang,
                "dir": "rtl" if lang == "ar" else "ltr",
                "t": translations
            })
        
        request.session["user"] = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "can_view_finance": user.can_view_finance,
            "language": user.preferred_language
        }
        
        logger.info(f"User {username} logged in successfully")
        return RedirectResponse("/", status_code=303)
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "حدث خطأ أثناء تسجيل الدخول",
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
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
        
        pending_approval = db.query(TestOrder).filter(
            TestOrder.result_file.isnot(None),
            TestOrder.admin_approved == False
        ).count()
        
        employee = None
        if user.get("role") == "admin":
            employee = db.query(User).filter(User.username == "staff").first()
        
        settings = get_or_create_settings(db)
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("dashboard.html", {"request": request, "patient_count": p_count, "order_count": o_count, "today_orders": today_orders, "pending_results": pending_results, "pending_approval": pending_approval, "user": user, "employee": employee, "settings": settings, "lang": lang, "dir": "rtl" if lang == "ar" else "ltr", "t": translations, "show_finance": settings.show_finance_to_users})
    
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
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("patients.html", {
            "request": request,
            "patients": patients,
            "search": search or "",
            "user": user,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
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
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("patient_history.html", {
            "request": request,
            "patient": patient,
            "user": user,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
        })
    
    except HTTPException as he:
        if he.status_code == 401:
            return RedirectResponse("/login", status_code=303)
        raise

@app.post('/delete_patient/{patient_id}')
def delete_patient(patient_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        require_admin(request)
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient:
            # حذف الطلبات المرتبطة أولاً لمنع تعارض قاعدة البيانات
            db.query(TestOrder).filter(TestOrder.patient_id == patient_id).delete()
            db.delete(patient)
            db.commit()
            logger.info(f"Patient {patient.id} deleted by admin")
        return RedirectResponse('/patients', status_code=303)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.get('/edit_patient/{patient_id}')
def edit_patient_page(patient_id: int, request: Request, db: Session = Depends(get_db)):
    # هذه الدالة لفتح الصفحة فقط (GET)
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return RedirectResponse("/patients")
    
    lang = get_language(request, db)
    translations = get_translations(request, db)
    return templates.TemplateResponse("edit_patient.html", {
        "request": request, 
        "patient": patient, 
        "t": translations, 
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr"
    })

@app.post('/edit_patient/{patient_id}')
def edit_patient(
    patient_id: int, request: Request,
    name: str = Form(...), phone: str = Form(...),
    age: int = Form(None), gender: str = Form(None),
    address: str = Form(None), notes: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        require_admin(request)
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient:
            patient.name, patient.phone = name, phone
            patient.age, patient.gender = age, gender
            patient.address, patient.notes = address, notes
            db.commit()
        return RedirectResponse(f'/patient_details/{patient_id}', status_code=303)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.get('/search_patients')
def search_patients(query: str, db: Session = Depends(get_db)):
    try:
        patients = db.query(Patient).filter(
            or_(Patient.name.ilike(f"%{query}%"), Patient.phone.ilike(f"%{query}%"))
        ).limit(10).all()
        return [{"name": p.name, "phone": p.phone or ""} for p in patients]
    except Exception as e:
        logger.error(f"Search error: {e}")
        return []

@app.get('/add_patient', response_class=HTMLResponse)
def add_patient_page(request: Request, db: Session = Depends(get_db)):
    # جرب تعطيل هذا السطر مؤقتاً بوضع # قبله
    # user = get_current_user(request) 
    
    lang = get_language(request, db)
    translations = get_translations(request, db)
    return templates.TemplateResponse("add_patient.html", {
        "request": request, "t": translations, "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr", "search": ""
    })

@app.post('/add_patient')
def add_patient_submit(
    request: Request, 
    name: str = Form(...), 
    phone: str = Form(...),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        # إنشاء مريض جديد بكافة البيانات
        new_patient = Patient(
            name=name, 
            phone=phone, 
            age=age, 
            gender=gender, 
            address=address,
            notes=notes
        )
        db.add(new_patient)
        db.commit()
        return RedirectResponse('/patients', status_code=303)
    except Exception as e:
        logger.error(f"Error saving patient: {e}")
        db.rollback()
        return RedirectResponse('/patients', status_code=303)

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
        elif status == "pending_approval":
            query = query.filter(
                TestOrder.result_file.isnot(None),
                TestOrder.admin_approved == False
            )
        
        orders = query.order_by(TestOrder.created_at.desc()).all()
        settings = get_or_create_settings(db)
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("orders.html", {
            "request": request,
            "orders": orders,
            "status_filter": status,
            "publish_link": settings.publish_link,
            "user": user,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
        })
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.get('/add_order', response_class=HTMLResponse)
def add_order_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = get_current_user(request)
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("add_order.html", {
            "request": request, 
            "user": user,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
        })
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.post('/add_order')
def add_order(
    request: Request,
    name: str = Form(...),
    phone: str = Form(...),
    test: str = Form(...),
    price: int = Form(...),
    # الخانات الجديدة التي أضفناها في HTML
    age: str = Form(None),
    gender: str = Form(None),
    address: str = Form(None),
    currency: str = Form("ج.م"),
    db: Session = Depends(get_db)
):
    try:
        user = get_current_user(request)
        
        if not phone or not phone.strip():
            raise HTTPException(status_code=400, detail="رقم الهاتف مطلوب")
        
        # نستخدم نفس الكلاس الخاص بك لبيانات الطلب
        order_data = OrderCreate(name=name, phone=phone, test=test, price=price, currency=currency)
        
        # البحث بنفس طريقتك الأصلية (تطابق الاسم والهاتف)
        patient = db.query(Patient).filter(
            Patient.name == name, 
            Patient.phone == phone
        ).first()

        if not patient:
            # مريض جديد: ننشئ المريض مع كل البيانات الجديدة
            patient = Patient(
                name=name, 
                phone=phone,
                age=age,
                gender=gender,
                address=address
            )
            db.add(patient)
            db.commit()
            db.refresh(patient)
        else:
            # مريض موجود: نحدث تاريخ الزيارة والبيانات في حال إدخالها/تغييرها
            patient.last_visit = datetime.now()
            if age: patient.age = age
            if gender: patient.gender = gender
            if address: patient.address = address
            db.commit()
        
        # توليد PIN فريد كما في كودك الأصلي
        pin = generate_secure_pin(order_data.phone)
        while db.query(TestOrder).filter(TestOrder.pin == pin).first():
            pin = generate_secure_pin(order_data.phone)
        
        # إنشاء الطلب
        new_order = TestOrder(
            patient_id=patient.id,
            patient_name=patient.name,
            test_name=order_data.test,
            price=order_data.price,
            currency=currency,
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
async def upload_result(order_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
        if not order: 
            raise HTTPException(status_code=404)
        
        # التأكد من البيانات قبل الرفع
        patient = db.query(Patient).filter(Patient.id == order.patient_id).first()
        if not patient.phone or not order.price or order.price <= 0:
            return RedirectResponse('/orders?error=missing_data', status_code=303)

        # قراءة محتوى الملف
        content = await file.read()
        file_ext = os.path.splitext(file.filename)[1].lower()
        safe_filename = f"{order.pin}_{datetime.now().strftime('%H%M%S')}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # حفظ الملف محلياً
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # --- إرسال النتيجة أونلاين إلى الرابط المحدد ---
        try:
            import requests
            online_url = settings.publish_link if 'settings' in locals() else FAKE_PUBLISH_LINK
            with open(file_path, "rb") as f:
                response = requests.post(
                    online_url, 
                    data={
                        "pin": order.pin, 
                        "patient": order.patient_name, 
                        "test": order.test_name,
                        "phone": patient.phone, 
                        "price": order.price,
                        "currency": order.currency
                    },
                    files={"file": (safe_filename, f)},
                    timeout=30
                )
                if response.status_code == 200:
                    logger.info(f"Result sent online for order {order.pin}")
                else:
                    logger.warning(f"Online upload failed with status {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending result online: {e}")
        # --- نهاية الإرسال أونلاين ---

        # تحديث حالة الطلب
        order.result_file = file_path
        order.published = False
        order.admin_approved = False
        db.commit()
        
        return RedirectResponse('/orders', status_code=303)
    except Exception as e:
        logger.error(f"Upload error: {e}")
        return RedirectResponse('/orders', status_code=303)

@app.post('/admin_approve_order/{order_id}')
def admin_approve_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    user = request.session.get("user")
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403)
    
    order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
    if order and order.result_file:
        order.admin_approved = True
        order.published = True
        db.commit()
    return RedirectResponse('/orders', status_code=303)

@app.post('/approve_result/{order_id}')
def approve_result(order_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        user = require_admin(request)
        
        order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
        if order and order.result_file:
            order.admin_approved = True
            order.published = True
            db.commit()
            logger.info(f"Result for order {order.pin} approved and published by admin")
        
        return RedirectResponse('/orders', status_code=303)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.post('/republish_result/{order_id}')
def republish_result(order_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        user = require_admin(request)
        
        order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
        if order and order.result_file and os.path.exists(order.result_file):
            order.published = True
            order.admin_approved = True
            db.commit()
            logger.info(f"Result for order {order.pin} republished by admin")
        
        return RedirectResponse('/orders', status_code=303)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

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
        
        # جلب الإعدادات للتأكد من حالة زر المالية
        settings = get_or_create_settings(db)
        
        # إذا لم يكن مديراً وكان خيار المالية مغلقاً في الإعدادات، يتم منعه
        if user.get("role") != "admin" and not settings.show_finance_to_users:
            raise HTTPException(status_code=403, detail="ليس لديك صلاحية للوصول للحسابات")
        
        query = db.query(TestOrder)
        
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(TestOrder.created_at >= start)
        else:
            query = query.filter(func.date(TestOrder.created_at) == date.today())
        
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            end = end.replace(hour=23, minute=59, second=59)
            query = query.filter(TestOrder.created_at <= end)
        
        orders = query.all()
        total = sum(o.price for o in orders)
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("finance.html", {
            "request": request,
            "orders": orders,
            "total": total,
            "start_date": start_date or date.today().strftime('%Y-%m-%d'),
            "end_date": end_date or "",
            "user": user,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
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
        user = require_admin(request)
        
        staff = db.query(User).filter(User.username == "staff").first()
        if staff:
            staff.can_view_finance = finance_access is not None
            db.commit()
            logger.info(f"Staff finance permission updated: {staff.can_view_finance}")
        
        return RedirectResponse("/", status_code=303)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        logger.error(f"Update permission error: {e}")
        return RedirectResponse("/", status_code=303)
    
@app.get('/settings', response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_admin(request)
        
        settings = get_or_create_settings(db)
        
        lang = get_language(request, db)
        translations = get_translations(request, db)
        
        return templates.TemplateResponse("settings.html", {
            "request": request,
            "settings": settings,
            "user": user,
            "lang": lang,
            "dir": "rtl" if lang == "ar" else "ltr",
            "t": translations
        })
    
    except HTTPException:
        return RedirectResponse("/login", status_code=303)

@app.post('/update_settings')
def update_settings(
    request: Request,
    publish_link: str = Form(...),
    lab_name: str = Form(...),
    default_language: str = Form("ar"),
    show_language: Optional[str] = Form(None),
    finance_access: Optional[str] = Form(None), 
    db: Session = Depends(get_db)
):
    try:
        user = require_admin(request)
        settings = get_or_create_settings(db)
        
        # حفظ البيانات الأساسية
        settings.publish_link = publish_link
        settings.lab_name = lab_name
        settings.default_language = default_language
        settings.show_language_to_users = (show_language == "on")
        
        # القيمة القادمة من المتصفح (True إذا كانت مفعلة)
        is_checked = (finance_access == "on")
        
        # --- محاولة الحفظ الذكي ---
        # سنحاول البحث عن اسم الحقل الصحيح في قاعدة بياناتك أياً كان اسمه
        found_field = False
        for field in ['show_finance_to_users', 'can_view_finance', 'finance_access', 'show_finance']:
            if hasattr(settings, field):
                setattr(settings, field, is_checked)
                found_field = True
                break
        
        if not found_field:
            logger.warning("لم يتم العثور على حقل المالية في قاعدة البيانات")
        
        settings.updated_at = datetime.now()
        db.commit()
        
        if "user" in request.session:
            request.session["user"]["language"] = default_language
            
        return RedirectResponse("/settings", status_code=303)
    except Exception as e:
        logger.error(f"خطأ الحفظ: {e}")
        return RedirectResponse("/settings", status_code=303)
    
# --- Patient Portal (Public) ---
@app.get('/update_portal_language')
def update_portal_language(request: Request, lang: str, redirect: str = "/online_results"):
    """
    تغيير اللغة للواجهة العامة (دون تسجيل دخول)
    """
    # حفظ اللغة في الجلسة للواجهة العامة
    request.session["portal_language"] = lang
    
    # العودة للصفحة المطلوبة
    return RedirectResponse(redirect, status_code=303)

@app.get('/online_results', response_class=HTMLResponse)
def patient_portal(request: Request, db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    
    # الحصول على لغة البوابة من الجلسة أو الإعدادات الافتراضية
    portal_lang = request.session.get("portal_language", settings.default_language)
    
    # الحصول على الترجمات
    lang = portal_lang
    dir = "rtl" if lang == "ar" else "ltr"
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["ar"])
    
    return templates.TemplateResponse("patient_portal.html", {
        "request": request,
        "settings": settings,
        "lang": lang,
        "dir": dir,
        "t": translations
    })

@app.post('/check_online')
def check_online(
    pin: str = Form(...), 
    extra_info: str = Form(...),  # استقبال القيمة الثانية (هاتف أو اسم) من المستخدم
    db: Session = Depends(get_db)
):
    try:
        # هنا نقوم بعملية استعلام معقدة (Join) تربط جدول الطلبات بجدول المرضى
        # لكي نتمكن من الوصول لرقم الهاتف الموجود في جدول المرضى
        order = db.query(TestOrder).join(Patient).filter(
            TestOrder.pin == pin.strip(),            # الشرط الأول: مطابقة الرقم السري
            TestOrder.published == True,             # الشرط الثاني: أن تكون النتيجة منشورة
            TestOrder.admin_approved == True,        # الشرط الثالث: أن تكون معتمدة من الإدارة
            
            # الشرط الرابع (الميزة الجديدة): 
            # يجب أن تطابق القيمة المدخلة (extra_info) إما رقم الهاتف في جدول المرضى
            # أو اسم المريض المسجل في طلب التحليل
            or_(
                Patient.phone == extra_info.strip(),
                TestOrder.patient_name.like(f"{extra_info.strip()}%")
            )
        ).first()
        
        # إذا تحقق كل ما سبق بنجاح
        if order:
            return JSONResponse({
                "status": "success",
                "patient": order.patient_name,
                "test": order.test_name,
                "file": f"/{order.result_file}",
                "date": order.created_at.strftime('%Y-%m-%d'),
                "currency": order.currency
            })
        
        # إذا لم يتطابق الـ PIN أو لم تتطابق البيانات الإضافية
        return JSONResponse({
            "status": "not_found",
            "message": "بيانات التحقق غير صحيحة، يرجى التأكد من الرقم السري ورقم الهاتف"
        })
    
    except Exception as e:
        # تسجيل الخطأ في السجل (Logging) لضمان عدم ضياع أي تفاصيل تقنية
        logger.error(f"Check online error: {e}")
        return JSONResponse({
            "status": "error",
            "message": "حدث خطأ تقني أثناء معالجة طلبك"
        })
    
@app.get('/my_settings', response_class=HTMLResponse)
def my_settings_page(request: Request, db: Session = Depends(get_db)):
    user_data = request.session.get("user")
    if not user_data:
        return RedirectResponse("/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["id"]).first()
    settings = db.query(SystemSettings).first()
    
    lang = get_language(request, db)
    translations = get_translations(request, db)
    
    return templates.TemplateResponse("profile_settings.html", {
        "request": request, 
        "user": user, 
        "settings": settings,
        "msg": request.query_params.get("msg"),
        "lang": lang,
        "dir": "rtl" if lang == "ar" else "ltr",
        "t": translations
    })

@app.post('/update_profile')
def update_profile(
    request: Request,
    new_username: str = Form(...),
    new_password: str = Form(None),
    db: Session = Depends(get_db)
):
    user_data = request.session.get("user")
    if not user_data:
        return RedirectResponse("/login", status_code=303)
    
    user = db.query(User).filter(User.id == user_data["id"]).first()
    
    # التأكد أن اسم المستخدم الجديد ليس محجوزاً لشخص آخر
    existing_user = db.query(User).filter(User.username == new_username, User.id != user.id).first()
    if existing_user:
        return RedirectResponse("/my_settings?msg=username_taken", status_code=303)

    user.username = new_username
    if new_password and len(new_password) >= 6:
        user.password = hash_password(new_password)
    
    db.commit()
    
    # تحديث بيانات الجلسة بالاسم الجديد
    request.session["user"]["username"] = new_username
    
    return RedirectResponse("/my_settings?msg=success", status_code=303)

# --- تغيير اللغة ---
@app.post('/update_language')
def update_language(
    request: Request, 
    lang: str = Form(...), 
    db: Session = Depends(get_db)
):
    try:
        user_data = request.session.get("user")
        if not user_data: 
            return RedirectResponse("/login", status_code=303)
        
        settings = get_or_create_settings(db)
        
        # التحقق: هل المستخدم أدمن؟ أو هل الأدمن سمح للموظفين بتغيير اللغة؟
        is_admin = user_data.get("role") == "admin"
        can_change = settings.show_language_to_users

        if is_admin or can_change:
            user = db.query(User).filter(User.id == user_data["id"]).first()
            if user:
                user.preferred_language = lang
                db.commit()
                
                # تحديث الجلسة فوراً لتعكس اللغة الجديدة
                request.session["user"]["language"] = lang
                logger.info(f"Language updated to {lang} for user {user.username}")
        
        # العودة للصفحة السابقة
        referer = request.headers.get("referer", "/")
        return RedirectResponse(referer, status_code=303)
    
    except Exception as e:
        logger.error(f"Update language error: {e}")
        return RedirectResponse("/", status_code=303)

# --- إدارة الطلبات (تعديل وحذف) ---

@app.get("/edit_order/{order_id}")
async def edit_order_form(request: Request, order_id: int, db: Session = Depends(get_db)):
    order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
    if not order:
        return RedirectResponse(url="/orders", status_code=303)
    lang = get_language(request, db)
    translations = get_translations(request, db)
    return templates.TemplateResponse("edit_order.html", {
        "request": request, "order": order, "t": translations,
        "lang": lang, "dir": "rtl" if lang == "ar" else "ltr"
    })

@app.post("/edit_order/{order_id}")
async def update_order(
    order_id: int, request: Request, # أضفنا request هنا للأمان
    test_name: str = Form(...), price: float = Form(...), 
    pin: str = Form(...), db: Session = Depends(get_db)
):
    require_admin(request) # حماية التعديل
    order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
    if order:
        order.test_name, order.price, order.pin = test_name, price, pin
        db.commit()
    return RedirectResponse(url="/orders", status_code=303)

@app.post('/delete_order/{order_id}')
def delete_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        require_admin(request)
        order = db.query(TestOrder).filter(TestOrder.id == order_id).first()
        if order:
            # حذف الملف الفيزيائي أولاً
            if order.result_file and os.path.exists(order.result_file):
                try: os.remove(order.result_file)
                except: pass
            db.delete(order)
            db.commit()
            logger.info(f"Order {order_id} deleted with its file")
        return RedirectResponse('/orders', status_code=303)
    except HTTPException:
        return RedirectResponse("/login", status_code=303)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
