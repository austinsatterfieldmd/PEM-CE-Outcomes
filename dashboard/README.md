# CME Question Explorer Dashboard

A modern web dashboard for searching and exploring CME outcomes questions with tags and performance metrics.

## Features

- **Full-text search** across questions and answers
- **Multi-filter support** for Topic, Disease State, Treatment, Biomarker, Trial, and more
- **Performance metrics** with pre/post scores and knowledge gain visualization
- **Audience segmentation** - view metrics by overall, medical oncologists, academic vs community
- **Question details** - view full question, answers, tags, and performance data

## Deployment Options

### Option 1: Vercel (Production)

The dashboard is configured for one-click deployment to Vercel.

1. **Push to GitHub** - Commit the `dashboard/` folder to your repository
2. **Import to Vercel**:
   - Go to [vercel.com](https://vercel.com) and create new project
   - Import from GitHub
   - Set **Root Directory** to `dashboard`
3. **Deploy** - Vercel auto-detects the configuration

The deployed dashboard includes:
- Static React frontend
- Python serverless API functions
- Bundled SQLite database (read-only)

### Option 2: Local Development

#### Prerequisites

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)

#### 1. Start the Backend

```bash
# From the project root
cd CME-Outcomes-Tagger_v2

# Install Python dependencies
pip install fastapi uvicorn pydantic pandas openpyxl

# Import data into database (first time only)
python dashboard/scripts/import_data.py

# Start the API server
python -m uvicorn dashboard.backend.main:app --reload --port 8000
```

The API will be available at http://localhost:8000 with docs at http://localhost:8000/docs

#### 2. Start the Frontend

```bash
# Navigate to frontend directory
cd dashboard/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The dashboard will be available at http://localhost:5173

## Architecture

```
dashboard/
├── api/               # Vercel serverless functions
│   ├── _shared/       # Shared database access
│   ├── questions/     # Question endpoints
│   └── reports/       # Report endpoints
├── backend/           # FastAPI backend (local dev)
│   ├── main.py        # Application entry point
│   ├── routers/       # API routes
│   ├── services/      # Business logic
│   └── models/        # Pydantic schemas
├── frontend/          # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── services/    # API client
│   │   └── types.ts     # TypeScript types
│   └── package.json
├── scripts/           # Utility scripts
│   └── import_data.py # Data import
├── data/              # SQLite database
└── vercel.json        # Vercel deployment config
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/questions/search` | POST | Search with filters |
| `/api/questions/search` | GET | Simple search |
| `/api/questions/{id}` | GET | Get question details |
| `/api/questions/filters/options` | GET | Get available filter values |
| `/api/questions/filters/options/dynamic` | POST | Get dynamic filter options |
| `/api/questions/stats/summary` | GET | Get database statistics |
| `/api/reports/aggregate/by-tag` | POST | Aggregate by tag field |
| `/api/reports/aggregate/by-demographic` | POST | Aggregate by demographic |
| `/api/reports/trends` | POST | Performance trends |
| `/api/reports/activities` | GET | List activities |
| `/api/reports/options/demographics` | GET | Demographic filter options |
| `/health` | GET | Health check (local only) |

## Data Structure

The dashboard imports questions from Excel files with:

- **Question text** and answers (correct + incorrect)
- **Tags**: Topic, Disease State, Disease Stage, Disease Type, Treatment, Biomarker, Trial
- **Performance metrics**: Pre/Post scores with sample sizes
- **Audience segments**: Overall, Medical Oncologists, Academic, Community
- **Activity associations**: Which CME programs used each question

## Development

### Backend (Python - Local)

```bash
# Run with auto-reload
python -m uvicorn dashboard.backend.main:app --reload --port 8000

# Run import script
python dashboard/scripts/import_data.py
```

### Frontend (React)

```bash
cd dashboard/frontend

# Development
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Database

The dashboard uses SQLite for simplicity. The database file is stored at:
```
dashboard/data/questions.db
```

To reset the database, delete this file and run the import script again.

**Note**: On Vercel, the database is bundled as a read-only asset. For write operations (tag editing), future integration with Snowflake is planned.

## Customization

### Adding new filters

1. Add the field to `dashboard/backend/models/schemas.py`
2. Update `SearchFilters` and query logic in `database.py`
3. Add filter UI in `FilterPanel.tsx`
4. For Vercel: Update the corresponding serverless function in `api/`

### Styling

The frontend uses Tailwind CSS with a custom color palette. Edit `tailwind.config.js` to customize colors and fonts.
