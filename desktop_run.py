import webview # تحتاج لتثبيت: pip install pywebview
import threading
import uvicorn
import sys
import os
from main import app

# دالة لتشغيل السيرفر في الخلفية
def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, debug=False)

if __name__ == "__main__":
    # 1. تشغيل السيرفر في "خيط" منفصل (Thread)
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # 2. إنشاء نافذة ويندوز حقيقية
    # يمكنك تغيير العنوان وحجم النافذة هنا
    webview.create_window('نظام المختبر الطبي - د. ياسر', 'http://127.0.0.1:8000/login', 
                          width=1200, height=800, resizable=True)
    
    # 3. ابدأ تشغيل النافذة
    webview.start()
