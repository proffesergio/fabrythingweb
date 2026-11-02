<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0F172A,100:EC4899&height=180&section=header&text=Fabrything&fontSize=40&fontColor=fff&animation=fadeIn&fontAlignY=35&desc=Modern%20E-commerce%20Platform%20for%20Bangladesh&descAlignY=55&descAlign=50" />

<div align="center">

### 🛍️ A modern ecommerce platform
**Fast, Bangla-ready, bKash/Nagad integrated - for Bangladeshi brands.**

[Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
[Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
[Next.js](https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
[Tailwind](https://img.shields.io/badge/Tailwind-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)

</div>

---

### Features

- 🛒 Product catalog with variants, Bangla description
- 💳 bKash, Nagad, COD, SSLCommerz
- 📦 Inventory, order tracking
- 🎨 Modern UI - Tailwind, mobile-first
- 📊 Admin dashboard - sales analytics
- 🚀 SEO optimized, fast

### Quick Start

```bash
git clone https://github.com/proffesergio/fabrythingweb.git
cd fabrythingweb

# Backend
cd backend/EcommerceInventory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Configure local database/settings before migrating.
python manage.py migrate
python manage.py runserver

# Frontend
cd ../../frontend/ecommerce_inventory
npm install
npm start
```

### Stack

- **Frontend:** React 18, Create React App, Material UI, Redux Toolkit
- **Backend:** Django 5, Django REST Framework
- **DB:** Neon PostgreSQL
- **Payments:** Shop orders use Cash on Delivery; food also supports bKash/Nagad
- **Deploy:** Vercel (frontend + Django API) + Neon Postgres

Production release and verification: [release status](docs/PRODUCTION_RELEASE.md).
Domain configuration: [Cloudflare DNS](docs/CLOUDFLARE_DNS_SETUP.md).

### Why Fabrything?

For PotakaIT.com experience - I built computer parts e-commerce from 0. This is v2, AI-powered.

### Roadmap

- [ ] AI product description generator (Bangla + English)
- [ ] AI chatbot for customer support

<div align="center">
E-commerce for Bangladesh, built in Bangladesh 🛍️
</div>
