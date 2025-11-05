# Bio Daily Research Digest

An automated system that fetches, analyzes, and emails relevant biomedical AI research papers from PubMed and bioRxiv daily.

## Features

- **Daily Digest**: Runs Monday-Friday at 9:00 AM Pacific Time
- **AI-Powered Analysis**: Uses Gemini 2.5 Pro to classify papers by relevance
- **Smart Filtering**: Focuses on AI/ML applications in medicine, drug discovery, diagnostics, and biotech
- **Beautiful Design**: Modern light-mode email template with clean, professional styling
- **Multi-Source**: Fetches from PubMed, bioRxiv, and medRxiv
- **Working Links**: Direct links to PDFs, code repositories, and datasets

## Production Setup

### 1. Environment Variables
Create a `.env` file in the project root:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
RESEND_API_KEY=your_resend_api_key_here
DATABASE_PATH=./digest.db
LOG_LEVEL=INFO
```

### 2. Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration
Update `config.yaml` with your email settings:
```yaml
digest:
  recipients:
    - "your-email@example.com"
  from_email: "digest@yourdomain.com"
  from_name: "Bio Daily Research Digest"
```

### 4. Scheduling
The system is configured to run Monday-Friday at 9:00 AM Pacific Time.

**Manual Run:**
```bash
python main.py --force  # Force run regardless of schedule
```

**Test Mode:**
```bash
python main.py --test --force  # Generate test email without sending
```

**Reset Database:**
```bash
python main.py --reset-db --force  # Clear history and reprocess all papers
```

## Architecture

- **Fetch**: PubMed API and bioRxiv/medRxiv RSS feeds
- **Classify**: Gemini AI analyzes relevance to AI in medicine, drug discovery, and biotech
- **Filter**: Heuristic and AI-based filtering for high-impact papers
- **Render**: Beautiful HTML email with clean, professional design
- **Send**: Email delivery via Resend API
- **Store**: SQLite database to track processed papers and avoid duplicates

## Research Categories

Papers are classified into buckets:
- **AI Diagnostics & Medical Imaging**: Radiology, pathology, CT/MRI analysis
- **Drug Discovery & Compound Screening**: Virtual screening, molecular docking, ADMET
- **Protein Modeling & Bioinformatics**: AlphaFold, structure prediction, proteomics
- **Clinical Decision Support & Predictive Analytics**: Risk prediction, early warning systems
- **Neuroscience & Brain-Computer Interfaces**: Neural decoding, cognitive analysis
- **EEG/fNIRS & Bio-signal Analysis**: Wearables, continuous monitoring
- **Genomics & Computational Biology**: RNA-seq, CRISPR, variant calling, single-cell
- **Healthcare AI Models & LLMs**: Clinical NLP, medical language models, EHR analysis
- **Datasets & Clinical Benchmarks**: Medical datasets, validation studies
- **Medical Robotics & Surgical AI**: Robotic surgery, minimally invasive procedures

## Production Deployment

For production deployment, consider:
- Cron job or systemd timer for scheduling
- Log rotation and monitoring
- Database backup strategy
- Error handling and alerting
- Rate limiting for API calls

## Development

```bash
# Send test email with sample papers
python send_test_email.py

# Run with verbose logging
python main.py --verbose --force

# Test new features
python test_new_features.py
```

## Configuration Details

### PubMed Queries
The system searches PubMed for papers matching AI/ML in:
- Medical diagnostics and imaging
- Drug discovery and compound screening
- Protein analysis and bioinformatics
- Clinical decision support
- Neuroscience and brain-computer interfaces

### bioRxiv/medRxiv
Fetches preprints from both bioRxiv and medRxiv within the specified lookback window (default: 1 day).

### Relevance Scoring
Papers are scored 0-100 based on:
- **Boost terms**: Clinical validation, FDA approval, large language models, AlphaFold
- **Core relevance**: AI/ML methodology applied to biomedical problems
- **Risk flags**: Animal-only studies, small samples, no code availability
- **Minimum score**: Papers below 50 are filtered out
