# Stocker-Project

📈 Stocker – AI-Powered Stock Trading Simulation

**Stocker** is a full-stack stock trading simulation platform built using **Flask (Python)** and integrated with **AWS DynamoDB** and **SNS**. It supports real-time dynamic stock prices, secure user roles (Admin/Trader), trade execution, portfolio management, and email alerts. Ideal for learning cloud-based financial app development.

---

## 🚀 Key Features

- 🔐 **Role-based Login/Signup** (Admin & Trader)
- 📊 **Real-time Stock Price Simulation**
- 💼 **Portfolio Management** with average price tracking
- 🧾 **Buy/Sell Transactions** with trade history
- 📧 **AWS SNS Email Notifications** (signup, trades, help)
- 🛠️ **Admin Dashboard** with platform analytics
- 📞 **Help/Contact Page** for support requests

---

## 🧱 Tech Stack

| Layer       | Technology         |
|-------------|--------------------|
| Backend     | Python (Flask)     |
| Database    | AWS DynamoDB       |
| Notification| AWS SNS            |
| Frontend    | HTML, CSS, JS      |
| Threads     | Python `threading` |
| Deployment  | Localhost / AWS EC2 (optional) |

---

## ⚙️ Setup Instructions

### 1. 📦 Install Dependencies

```bash
pip install -r requirements.txt

2. 🔐 AWS Configuration
Create an IAM user with DynamoDB + SNS permissions.

Configure AWS CLI:

bash
aws configure

3. ▶️ Run the App
bash
python aws_app.py

App will auto-open at: http://localhost:5000

🗃️ DynamoDB Tables
Table Name	Primary Key(s)	Description
stocker_user	email (S)	Stores user credentials
stocker_stocks	symbol (S)	Stores stock prices
stocker_portfolio	user_id (S), stock_symbol (S)	Tracks holdings per user
stocker_transactions	id (S)	Logs all buy/sell trades

🔔 AWS SNS Integration
Topic Name: stocker_alerts
Used to send:

✅ Welcome email on signup

✅ Trade confirmations

✅ Help messages

📌 Future Enhancements
📱 Responsive UI for mobile

🧠 AI-based trade recommendations

🤝 Contributing
Pull requests are welcome!
For major changes, open an issue first to discuss what you'd like to change.

🛡️ License
This project is licensed under the MIT License © 2025 Stocker Project.

👨‍💻 Developed By
Srinivasulu Reddy
With ❤️ from India
