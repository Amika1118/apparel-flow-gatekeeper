```markdown
# ApparelFlow ERP - Cutting Operations & Gatekeeper Terminal

A full-stack enterprise manufacturing checkpoint for the ApparelFlow ERP system[cite: 1]. Enforces server-side quality validation, component verification, and role-based access control before cut fabric enters the sewing assembly line[cite: 1, 2].

```

---

## ⚡ Quick Start

```bash
# 1. Clone & install
git clone [https://github.com/your-username/apparelflow-cutting-terminal.git](https://github.com/your-username/apparelflow-cutting-terminal.git)
cd apparelflow-cutting-terminal
npm install

# 2. Configure environment
cp .env.example .env.local

# 3. Setup database & seed pre-seeded recipes/users
npx prisma migrate dev
npx prisma db seed

# 4. Run development server
npm run dev

```

---

## 🔑 Demo Login Credentials

Switch personas using the UI Demo Switcher or login directly:

| Role | Email | Password | Scope |
| --- | --- | --- | --- |
| **Cutting Supervisor**<br> | `supervisor@apparelflow.com` | `SuperSecret123!` | Create cutting orders & input fabric yards

 |
| **Cutting Verifier**<br> | `verifier@apparelflow.com` | `VerifierPass123!` | Perform piece count QC, approve/reject batches

 |
| **Sewing Supervisor**<br> | `sewing@apparelflow.com` | `SewingPass123!` | Receive verified batches & start sewing assembly

 |

---

## 🛡️ Core Rules & Gatekeeper Logic

1. **Traffic Light Engine:** Component counts calculate in real time as **GREEN** (Match), **YELLOW** (Excess), or **RED** (Shortage).


2. **Server-Side Hard Stop:** Any order containing a **RED** (shortage) item strictly blocks approval at both the UI and backend API level (`422 Unprocessable Entity`).


3. **Role Isolation:** Non-verifier roles receive `403 Forbidden` if attempting to call verification endpoints.


4. **Query Isolation:** Sewing Queue endpoint strictly enforces `WHERE status = 'VERIFIED'`.



---

## 🧪 Automated Testing

Run the integration test suite covering RBAC, hard-stop validations, and query isolation:

```bash
npm run test

```

---

## 📄 Documentation

* [AI Optimization Report](https://www.google.com/search?q=./AI_OPTIMIZATION_REPORT.md)[cite: 5, 6]
* Live Demo: [https://apparelflow-verifier.vercel.app](https://www.google.com/search?q=https://apparelflow-verifier.vercel.app)[cite: 6]

```

```