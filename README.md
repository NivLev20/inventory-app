# Smart Retail Inventory – inventory-app

מערכת לניהול מלאי לרשת חנויות: מעקב אחרי כמויות בכל סניף, התראה על מוצרים שירדו מתחת למינימום, הזמנת מלאי בלחיצה אחת ודשבורד עם מגמות.

זהו **ריפו האפליקציה** של פרויקט הגמר (פרויקט #1). התשתית (Kubernetes, Jenkins, ניטור) נמצאת בריפו `inventory-devops`.

## מה יש כאן

```
inventory-app/
├── backend/                 Flask API (Python)
│   ├── app.py               כל ה-endpoints והלוגיקה
│   ├── db.py                חיבור למסד הנתונים (PostgreSQL, או SQLite בבדיקות)
│   ├── seed.py              נתוני דוגמה: 12 מוצרים ב-3 סניפים + היסטוריה של 14 יום
│   ├── tests/test_api.py    15 בדיקות אוטומטיות
│   ├── requirements.txt     ספריות להרצה
│   ├── requirements-dev.txt ספריות לבדיקות ול-lint
│   └── Dockerfile           בניית אימג' של ה-backend
├── frontend/                דשבורד (HTML + JavaScript + Chart.js)
│   ├── index.html / app.js / style.css
│   ├── nginx.conf.template  nginx מגיש את הדשבורד ומעביר /api ל-backend
│   └── Dockerfile           בניית אימג' של ה-frontend
└── docker-compose.yml       מריץ את הכל מקומית: DB + backend + frontend
```

## ארכיטקטורה

```
 דפדפן ──► frontend (nginx :8080) ──/api──► backend (Flask :5000) ──► PostgreSQL (:5432)
                                                  │
                                                  └── /metrics ──► Prometheus ──► Grafana
```

## הרצה מקומית (צריך רק Docker)

```bash
docker compose up --build
```

- דשבורד: http://localhost:8080
- API: http://localhost:5000/api/products
- בדיקת תקינות: http://localhost:5000/health

עצירה: `Ctrl+C` ואחר כך `docker compose down`. הנתונים נשמרים ב-volume בשם `pgdata`.

## הרצת הבדיקות וה-lint (בלי Docker)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
flake8 .
pytest -v
```

הבדיקות משתמשות ב-SQLite זמני, כך שהן לא צריכות PostgreSQL. ככה שלב הבדיקות ב-pipeline רץ מהר ופשוט.

## Endpoints

| Method | Path | מה עושה |
|---|---|---|
| GET | `/api/products` | כל המוצרים (סינון: `?store=Haifa&status=LOW`) |
| GET | `/api/products/<id>` | מוצר אחד |
| POST | `/api/products` | הוספת מוצר: `name`, `sku` (חובה), `stock`, `min_stock`, `price`, `category`, `store` |
| PUT | `/api/products/<id>` | עדכון מוצר או כמות |
| DELETE | `/api/products/<id>` | מחיקת מוצר |
| POST | `/api/products/<id>/restock` | הוספת מלאי: `quantity` (חובה), `note` |
| GET | `/api/restocks` | היסטוריית חידושי מלאי |
| GET | `/api/products/low-stock` | מוצרים שבמינימום או מתחתיו, כולל כמות מומלצת להזמנה |
| GET | `/api/products/analytics` | סיכומים ומגמות לדשבורד |
| GET | `/health` | liveness – האפליקציה רצה |
| GET | `/ready` | readiness – יש חיבור למסד הנתונים |
| GET | `/metrics` | מדדים ל-Prometheus |

דוגמה:

```bash
curl -X POST http://localhost:5000/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Laptop Stand","sku":"ELC-010","stock":4,"min_stock":10,"store":"Haifa","price":129}'

curl -X POST http://localhost:5000/api/products/1/restock \
  -H "Content-Type: application/json" -d '{"quantity":25,"note":"supplier order"}'
```

## הפיצ'רים ה"חכמים"

- **סטטוס אוטומטי לכל מוצר:** `OK`, `LOW` (במינימום או מתחתיו) או `OUT` (אזל).
- **כמות מומלצת להזמנה:** כמה צריך להזמין כדי להגיע לפעמיים המינימום. בדשבורד זה כפתור "Order X" בלחיצה אחת.
- **ריבוי סניפים:** לכל מוצר יש סניף, ואפשר לסנן לפיו.
- **שווי מלאי ומגמות:** סך היחידות לאורך 14 יום ויחידות שחודשו בכל יום.
- **מדדים עסקיים ל-Prometheus:** לא רק latency של ה-API, אלא גם `inventory_low_stock_products`, `inventory_out_of_stock_products`, `inventory_units_total` ו-`inventory_value`. כך אפשר להראות את מצב המלאי ב-Grafana ולהגדיר התראה.

## משתני סביבה (יוגדרו ב-Kubernetes דרך ConfigMap ו-Secret)

| משתנה | ברירת מחדל | הסבר |
|---|---|---|
| `DATABASE_URL` | `sqlite:///inventory.db` | כתובת ה-DB. ב-Docker/K8s: `postgresql://user:pass@host:5432/db` (**Secret**) |
| `APP_ENV` | `development` | שם הסביבה (**ConfigMap**) |
| `SEED_DATA` | `false` | `true` טוען נתוני דוגמה כשה-DB ריק (**ConfigMap**) |
| `BACKEND_URL` | `http://backend:5000` | (frontend) לאן nginx מעביר את `/api` (**ConfigMap**) |
