# Droyd Daily Robotics Research Digest

An automated system that fetches, analyzes, and emails relevant robotics research papers from arXiv daily.

## Features

- **Daily Digest**: Runs Monday-Friday at 5:00 PM Eastern Time
- **AI-Powered Analysis**: Uses Gemini 2.5 Pro to classify papers by relevance
- **Smart Filtering**: Focuses on dual-arm mobile manipulation research
- **Beautiful Design**: Modern light-mode email template with Droyd branding
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
  from_name: "Droyd Research Digest"
```

### 4. Scheduling
The system is configured to run Monday-Friday at 5:00 PM Eastern Time.

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

- **Fetch**: RSS feeds from arXiv cs.RO category
- **Classify**: Gemini AI analyzes relevance to dual-arm mobile manipulation
- **Filter**: Heuristic and AI-based filtering for quality papers
- **Render**: Beautiful HTML email with Droyd branding
- **Send**: Email delivery via Resend API

## Research Categories

Papers are classified into buckets:
- VLA / LLM-in-the-Loop
- Imitation / Diffusion / RL
- Perception for Manipulation
- Task & Motion Planning
- Datasets & Benchmarks
- Bimanual / Dual-Arm Manipulation
- Mobile Manipulation
- Hardware & Mechatronics
- HRI & Teleop
- Safety & Reliability

## Production Deployment

For production deployment, consider:
- Cron job or systemd timer for scheduling
- Log rotation and monitoring
- Database backup strategy
- Error handling and alerting
- Rate limiting for API calls

## Development

```bash
# Test the email template
python test_light_mode.py

# Send test email
python send_test_email.py

# Run with verbose logging
python main.py --verbose --force
```
