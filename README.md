# Abin Pharma

**Abin Pharma** is a comprehensive, enterprise-grade B2B pharmaceutical wholesale management platform. It is designed to serve pharmacies, hospitals, clinics, medical stores, distributors, and healthcare institutions with a modern, professional, and trustworthy healthcare-themed experience.

## Features Overview

- **B2B Wholesale Ordering:** Bulk order processing, quick order by SKU, Excel/CSV upload.
- **Dynamic Pricing:** Dealer pricing, dynamic discounts, and minimum order quantities.
- **Inventory Management:** Real-time stock monitoring, batch-wise inventory, low stock, and near-expiry alerts.
- **Dealer Management:** KYC registration, Drug License upload, Admin approval workflows, and Credit Account limits.
- **Prescription Module:** Prescription upload, pharmacist verification, and generic alternative suggestions.
- **Advanced Integrations:** 
  - JWT + OTP Authentication
  - Power BI for advanced analytics
  - n8n for automated alerts and notifications (email, WhatsApp)
  - Payment Gateways for secure checkout

## Technology Stack

- **Backend:** Django
- **Frontend:** HTML5, CSS3, JavaScript, Tailwind CSS
- **Database:** MySQL
- **Analytics:** Power BI
- **Automation:** n8n

## Setup Instructions (Phase 1)

1. **Clone the repository.**
2. **Set up Python Virtual Environment:**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Database Configuration:**
   - Ensure MySQL Server is running.
   - Update database credentials in the Django `settings.py` file.
5. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```
6. **Start the Development Server:**
   ```bash
   python manage.py runserver
   ```

## Development Phases
- **Phase 1:** Core setup, User Authentication (JWT+OTP), Role-Based access, and Homepage UI.
- **Phase 2:** Product & Inventory Management module.
- **Phase 3:** B2B E-commerce workflows (Cart, Checkout, Pricing).
- **Phase 4:** Order Management, Dealer Dashboards, returns.
- **Phase 5:** Automations (n8n), Analytics (Power BI), Prescription module, and optimizations.
