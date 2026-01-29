# 🔬 Laboratory Management System

A comprehensive web-based laboratory management system built with FastAPI and Bootstrap 5, featuring secure authentication, patient management, test ordering, and financial reporting.

## ✨ Features

### Core Features
- **🔐 Secure Authentication**: Bcrypt password hashing with role-based access control
- **👥 Patient Management**: Complete patient records with visit history
- **🧪 Test Order Management**: Create, track, and manage laboratory test orders
- **📊 Financial Reports**: Detailed revenue tracking with date filtering
- **📱 Patient Portal**: Public-facing portal for patients to check test results
- **🔑 Secure PIN System**: Auto-generated secure PINs for result retrieval
- **📄 File Upload**: Secure result file upload with validation

### Security Improvements
- ✅ Password hashing with bcrypt
- ✅ Role-based authorization (Admin/Staff)
- ✅ Input validation with Pydantic
- ✅ File type and size validation
- ✅ Secure PIN generation
- ✅ Proper error handling and logging

### User Interface
- 📱 Responsive Bootstrap 5 design
- 🌙 Modern gradient color schemes
- 🔍 Real-time patient autocomplete search
- 🖨️ Print-friendly financial reports
- 📊 Visual dashboard with statistics
- 🎨 Font Awesome icons throughout

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone or download the project**

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python main.py
```

4. **Access the system**
- Open your browser and navigate to: `http://localhost:8000`
- Default admin login: `admin` / `admin123`
- Default staff login: `staff` / `staff123`

## 📁 Project Structure

```
laboratory-management/
├── main.py                 # Main application file
├── requirements.txt        # Python dependencies
├── templates/             # HTML templates
│   ├── login.html
│   ├── dashboard.html
│   ├── patients.html
│   ├── patient_history.html
│   ├── orders.html
│   ├── add_order.html
│   ├── finance.html
│   ├── patient_portal.html
│   └── settings.html
├── static/                # Static files (CSS, images)
├── results_files/         # Uploaded test results
└── lab.db                 # SQLite database (auto-created)
```

## 👤 User Roles

### Admin
- Full system access
- View and manage all features
- Access financial reports
- Manage staff permissions
- Update system settings

### Staff/Employee
- Create and manage patients
- Create and manage test orders
- Upload test results
- Access financial reports (if granted by admin)

## 🔧 Configuration

### Environment Variables (Optional)
Create a `.env` file for production:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///lab.db
```

### System Settings
Access via: Dashboard → Settings (Admin only)
- Laboratory name
- Results publication link (update with your real domain)

## 📋 Usage Guide

### Creating a Test Order
1. Navigate to "إضافة طلب جديد" (Add New Order)
2. Search for existing patient or enter new patient details
3. Enter test name and price
4. System generates secure PIN automatically
5. Order is created and ready for result upload

### Uploading Results
1. Go to "التحاليل" (Orders)
2. Find the order (filter by status if needed)
3. Click file upload button
4. Select PDF, image, or document file
5. Result is published and patient can access via PIN

### Patient Results Portal
- Public portal at: `/online_results`
- Patients enter their PIN to retrieve results
- No login required
- Mobile-friendly interface

### Financial Reports
1. Navigate to "الحسابات" (Finance)
2. Filter by date range
3. View detailed transaction list
4. Print report for record-keeping

## 🔒 Security Features

1. **Password Security**: All passwords hashed with bcrypt
2. **File Validation**: Only allowed file types (.pdf, .jpg, .png, .docx)
3. **File Size Limits**: Maximum 10MB per file
4. **Secure PINs**: Cryptographically secure random generation
5. **Input Validation**: Pydantic models for all user inputs
6. **Error Handling**: Comprehensive try-catch blocks
7. **Logging**: All important actions logged

## 🛠️ Customization

### Adding Common Tests
Edit `add_order.html` datalist to include your frequently used tests:
```html
<datalist id="common-tests">
    <option value="Your Test Name">
    <!-- Add more options -->
</datalist>
```

### Changing Colors
Update the gradient colors in templates:
```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Adding More File Types
Update `ALLOWED_EXTENSIONS` in `main.py`:
```python
ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.docx', '.doc', '.xlsx'}
```

## 📊 Database Schema

### Users Table
- id, username, password (hashed), role, can_view_finance, created_at

### Patients Table
- id, name, phone, age, gender, address, last_visit, notes

### Test Orders Table
- id, patient_id, patient_name, test_name, price, pin, result_file, published, created_at, notes

### System Settings Table
- id, publish_link, lab_name, updated_at

## 🐛 Troubleshooting

### Database Issues
If database errors occur, delete `lab.db` and restart the application. Default users will be recreated.

### File Upload Fails
- Check file size (max 10MB)
- Verify file extension is allowed
- Ensure `results_files` directory has write permissions

### Login Issues
- Default credentials: admin/admin123 or staff/staff123
- Clear browser cache and cookies
- Check console for error messages

## 🔄 Future Enhancements

Potential improvements for production use:
- [ ] PostgreSQL/MySQL support for production
- [ ] Email notifications for ready results
- [ ] SMS integration for PIN delivery
- [ ] Advanced reporting and analytics
- [ ] Multi-language support
- [ ] Backup and restore functionality
- [ ] API documentation with Swagger
- [ ] User activity audit logs
- [ ] Dark mode support

## 📄 License

This project is provided as-is for educational and commercial use.

## 🤝 Support

For issues or questions:
1. Check the troubleshooting section
2. Review the code comments
3. Contact your development team

## ⚠️ Important Notes

1. **Production Deployment**: 
   - Change the SECRET_KEY before production use
   - Use a production database (PostgreSQL recommended)
   - Enable HTTPS/SSL
   - Set up proper backup procedures

2. **Data Privacy**: 
   - This system handles sensitive medical data
   - Ensure compliance with local healthcare regulations
   - Implement proper data retention policies

3. **Fake Publish Link**: 
   - Current publish link is temporary (`https://results.yourlab.com`)
   - Update in Settings when you have your real domain

---

**Built with ❤️ using FastAPI, Bootstrap 5, and modern web technologies**