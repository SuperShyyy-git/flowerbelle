# Flowerbelle Flower Shop POS System

**Web-based Point-of-Sale, Inventory Control System with Predictive Forecasting**

---

## 📋 Project Information

**Institution:** [Your University Name]  
**Course:** Information Systems Capstone Project  
**Academic Year:** 2024-2025

**Team Members:**
- [Member 1 Name] - Full Stack Developer
- [Member 2 Name] - Backend Developer
- [Member 3 Name] - Frontend Developer
- [Member 4 Name] - Database Administrator

**Project Adviser:** [Adviser Name]

**Client:** Flowerbelle Flower Shop

---

## 📝 Project Description

This system aims to modernize Flowerbelle Flower Shop's operations by providing:
- **Point-of-Sale Module** - Efficient transaction processing
- **Inventory Management** - Real-time stock tracking with alerts
- **Predictive Forecasting** - AI-powered demand prediction using Linear Regression
- **Reporting & Analytics** - Comprehensive business insights

---

## 🛠️ Technology Stack

### Backend
- **Framework:** Django 4.2 (Python)
- **API:** Django REST Framework
- **Database:** SQLite (Development), PostgreSQL (Production)
- **Authentication:** JWT (JSON Web Tokens)
- **ML Library:** scikit-learn

### Frontend
- **Framework:** React 18
- **Styling:** Tailwind CSS
- **Charts:** Recharts
- **HTTP Client:** Axios

### Development Tools
- **Version Control:** Git & GitHub
- **IDE:** Visual Studio Code
- **API Testing:** Postman
- **Methodology:** Agile (Scrum)

---

## 📦 Project Structure

```
flowerbelle-system/
├── backend/                  # Django backend
│   ├── accounts/            # User authentication
│   ├── inventory/           # Inventory management
│   ├── pos/                 # Point of sale
│   ├── reports/             # Analytics & reporting
│   ├── forecasting/         # Predictive models
│   ├── flowerbelle_backend/ # Django settings
│   ├── manage.py
│   └── requirements.txt
├── frontend/                # React frontend (coming soon)
├── docs/                    # Documentation
│   ├── SRS.md              # Requirements specification
│   ├── ERD.png             # Database diagram
│   └── API-docs.md         # API documentation
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Git

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

Access admin panel at: http://127.0.0.1:8000/admin

### Frontend Setup (Coming in Week 2)

```bash
# Navigate to frontend
cd frontend/flowerbelle-frontend

# Install dependencies
npm install

# Start development server
npm start
```

---

## 📅 Development Timeline

| Week | Focus | Status |
|------|-------|--------|
| Week 1 | Requirements & Setup | ✅ In Progress |
| Week 2 | Authentication & Backend Core | 🔄 Pending |
| Week 3 | Inventory Module | 🔄 Pending |
| Week 4 | POS Module | 🔄 Pending |
| Week 5 | Reports & Dashboard | 🔄 Pending |
| Week 6 | Predictive Forecasting | 🔄 Pending |
| Week 7 | Testing & Refinement | 🔄 Pending |
| Week 8 | Deployment & Training | 🔄 Pending |

---

## 🔑 Key Features

### 1. Point-of-Sale (POS)
- Fast product search and selection
- Multiple payment methods (Cash, Card, Digital)
- Automated receipt generation
- Sales history tracking

### 2. Inventory Management
- Real-time stock levels
- Stock-in/out tracking
- Low stock alerts
- Product categorization
- Supplier management

### 3. Predictive Forecasting
- Linear Regression model for demand prediction
- Seasonal trend analysis
- Stock recommendations
- Model accuracy metrics

### 4. Reporting & Analytics
- Sales reports (daily, weekly, monthly)
- Inventory valuation
- Top-selling products
- Staff performance tracking
- Visual dashboards with charts

### 5. User Management
- Role-based access control (Owner, Staff)
- Activity audit trail
- Secure authentication

---

## 📊 Database Schema

See `docs/ERD.png` for complete Entity Relationship Diagram.

**Main Entities:**
- Users
- Products
- Categories
- Suppliers
- Sales Transactions
- Inventory Movements
- Audit Logs
- Forecast Data

---

## 🧪 Testing

```bash
# Run backend tests
python manage.py test

# Run with coverage
coverage run manage.py test
coverage report
```

---

## 📖 Documentation

- **SRS Document:** `docs/SRS.md`
- **API Documentation:** `docs/API-docs.md`
- **User Manual:** `docs/user-manual.md` (Coming Soon)
- **Technical Guide:** `docs/technical-guide.md` (Coming Soon)

---

## 🤝 Contributing

This is a capstone project. Team members should:
1. Create a feature branch: `git checkout -b feature/feature-name`
2. Commit changes: `git commit -m "Description"`
3. Push to branch: `git push origin feature/feature-name`
4. Create Pull Request for team review

---

## 📄 License

This project is developed as an academic requirement and is intended for educational purposes.

---

## 📞 Contact

For questions or concerns, contact:
- **Team Lead:** [Email]
- **Project Adviser:** [Email]

---

## 🙏 Acknowledgments

- Flowerbelle Flower Shop for providing the opportunity
- [Adviser Name] for guidance and support
- [University Name] for resources and facilities

---

**Last Updated:** [Current Date]  
**Version:** 1.0.0 (Week 1)


# Backend Commands
cd backend
venv\Scripts\activate              # Activate environment
python manage.py runserver         # Start server
python manage.py makemigrations    # Create migrations
python manage.py migrate           # Apply migrations
python manage.py createsuperuser   # Create admin user
python manage.py test              # Run tests

# Git Commands
git status                         # Check changes
git add .                          # Stage all changes
git commit -m "message"            # Commit changes
git push                           # Push to remote
git pull                           # Pull latest changes