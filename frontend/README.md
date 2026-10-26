# AI Job Hunter — Frontend Web Application

Modern, responsive Next.js 16 web application designed for autonomous job discovery, resume matching, and auto-apply pipeline management.

---

## 🎨 Tech Stack & Design System

- **Framework**: Next.js 16 (App Router) + React 19
- **Styling**: Tailwind CSS + Custom Dark Glassmorphism Design System
- **State Management**: Zustand v5 with localStorage persistence (`store/authStore.ts`)
- **Data Fetching & Cache**: TanStack React Query v5 + Axios
- **Charts**: Recharts v3
- **Icons**: Lucide React
- **Typography**: Inter (Google Fonts)

---

## 📁 Directory Structure

```
frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/page.tsx          # Login & Register authentication portal
│   │   └── register/page.tsx       # Direct registration route
│   ├── (dashboard)/
│   │   ├── layout.tsx              # Protected dashboard shell & sidebar
│   │   ├── page.tsx                # Analytics dashboard with activity chart
│   │   ├── jobs/page.tsx           # Job discovery, filters & card grid
│   │   ├── applications/page.tsx   # Application queue & review slide drawer
│   │   ├── resumes/page.tsx        # Drag & drop resume manager
│   │   └── settings/page.tsx       # Auto-apply parameters & candidate profile
│   ├── globals.css                 # Dark glassmorphism styles & variables
│   ├── layout.tsx                  # Root HTML shell
│   └── providers.tsx               # QueryClient & Toast context providers
├── components/
│   ├── layout/
│   │   └── Sidebar.tsx             # Collapsible modern navigation sidebar
│   └── ui/
│       └── ToastProvider.tsx       # Toast notifications provider
├── lib/
│   ├── api.ts                      # Axios instance with JWT interceptor & API methods
│   └── utils.ts                    # Class name merging, dates & score formatters
└── store/
    └── authStore.ts                # Zustand auth state
```

---

## 🚀 Running the Frontend

To start only the frontend independently:

```bash
cd frontend
npm install
npm run dev
```

The frontend will run on [http://localhost:3000](http://localhost:3000).

*(To start both backend and frontend together with 1 command, run `python run.py` or `start.bat` from the root folder).*

---

## 🔧 Environment Variables (`.env.local`)

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```
