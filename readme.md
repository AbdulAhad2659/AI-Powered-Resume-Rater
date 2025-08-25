# AI-Powered Resume Rater

![python](https://img.shields.io/badge/python-3.11+-blue.svg)
![fastapi](https://img.shields.io/badge/FastAPI-0.116-green.svg)
![license](https://img.shields.io/badge/License-MIT-yellow.svg)

An intelligent FastAPI application to automatically score, analyze, and rank resumes against a job description using advanced AI models (Google Gemini & Groq Llama 3), a comprehensive scoring algorithm, and a user-friendly web interface.

---

## 📑 Table of Contents

- [✨ Key Features](#-key-features)
- [🛠️ Tech Stack](#️-tech-stack)
- [🚀 Getting Started](#-getting-started)
  - [1. Prerequisites](#1-prerequisites)
  - [2. Install](#2-install)
  - [3. Configuration](#3-configuration)
  - [4. Running the Application](#4-running-the-application)
- [📁 Project Structure](#-project-structure)
- [⚙️ API Endpoints](#️-api-endpoints)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)
- [📬 Contact](#-contact)

---

## ✨ Key Features

- **Advanced AI Analysis** — Primary analysis via Google Gemini with a seamless fallback to Groq's GPT-4o for resilience and speed.
- **Comprehensive Scoring System** — Goes beyond keyword matching and evaluates:
  - Skill Match & Context: Detects required skills and the context in which they're used.
  - Experience Relevance: Measures relevance of past roles and estimates years of experience.
  - Impact & Achievements: Finds quantified achievements, action verbs, and impact statements.
  - Education & Projects: Accounts for academic background and portfolio work.
- **Batch Processing** — Upload and evaluate dozens of resumes against a single job description.
- **Robust File Parsing** — Reliable text extraction from complex PDF and DOCX layouts.
- **Automated Recommendations** — Generates a `recommended_candidates.txt` file with top candidates, their scores, strengths, and suggested next steps.
- **AI-Generated Feedback** — Creates candidate feedback PDFs for those not selected to improve candidate experience.
- **Text-to-Speech (TTS) Summaries** — Produces audio summaries of evaluations (single-resume mode).
- **Interactive Web UI** — Clean drag-and-drop interface for uploads and clear visualization of results.

---

## 🛠️ Tech Stack

- **Backend:** FastAPI, Uvicorn
- **AI / LLMs:** Google Gemini, Groq (GPT-4o)
- **File Parsing:** PyMuPDF (fitz), python-docx
- **PDF Generation:** fpdf2
- **Frontend:** HTML5, CSS3, JavaScript (vanilla)
- **Language:** Python 3.11+

---

## 🚀 Getting Started

Follow the steps below to run the project locally.

### 1. Prerequisites

- Python 3.11 or higher
- `pip` and `venv`

### 2. Install

```bash
# Clone the repository
git clone https://github.com/abdulahad2659/resume-rater.git
cd resume-rater

# Create and activate virtual environment
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r reqs.txt
```

### 3. Configuration

Update the `.env` or create a `.env` file in the project root and set your keys and basic options:

```env
# --- API Keys (Required) ---
GOOGLE_API_KEY="your_google_api_key_here"
GROQ_API_KEY="your_groq_api_key_here"

# --- Optional configuration ---
AUDIO_SAVE_DIR="./tts_outputs"
RECOMMENDED_FILE="./recommended_candidates.txt"
STATIC_DIR="./static"
```

### 4. Running the Application

```bash
uvicorn app:app --reload
```

- Open the Web UI at: `http://127.0.0.1:8000`
- API docs (Swagger): `http://127.0.0.1:8000/docs`

---

## 📁 Project Structure

```
/Resume Rater
├── .venv/                  # Virtual environment
├── static/
│   └── index.html          # Frontend single-page application
├── tts_outputs/            # Saved audio files
├── .env                    # Environment variables (API keys, config)
├── app.py                  # Main FastAPI application
├── config.py               # Configuration loader, logger, API clients
├── feedback.py             # Candidate feedback PDF generation
├── llm_utils.py            # Interactions with Gemini & Groq
├── models.py               # Pydantic request/response models
├── openapi_patch.py        # Multi-file upload support for FastAPI docs
├── parsing.py              # PDF / DOCX text extraction
├── reqs.txt                # Python package dependencies
├── scoring.py              # Core scoring algorithm
├── service.py              # Orchestration/business logic
├── skills.py               # Skill normalization & matching
└── utils.py                # Helper utilities
```

---

## ⚙️ API Endpoints

- `GET /` — Serves the main HTML web interface.
- `POST /rate` — Analyze a single resume vs. a job description.
- `POST /batch-rate` — Analyze multiple resumes in batch.
- `GET /download-recommended` — Download the `recommended_candidates.txt` from a batch run.
- `GET /audio/{filename}` — Serve generated TTS audio files.
- `GET /health` — Health check endpoint showing status and configuration info.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Add tests where possible and keep changes scoped and documented.

---

## 📄 License

This project is licensed under the **MIT License** — see the `LICENSE.md` file for details.

---

## 📬 Contact

Questions or feature requests? Open an issue or reach out to the repository owner at `abdulahad2659` on GitHub.

---
