#!/usr/bin/env python3
"""
Send a test email with the new light-mode design using mock data.
"""

import yaml
import os
from render import EmailRenderer
from send import ResendClient
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Mock data for testing - Biomedical AI papers
mock_papers = [
    {
        'arxiv_id': '10.1101/2025.10.18.680935',
        'title': 'Advancing Protein Ensemble Predictions Across the Order-Disorder Continuum',
        'abstract': 'While deep learning has transformed structure prediction for ordered proteins, intrinsically disordered proteins remain poorly predicted. This paper introduces PeptoneBench and PepTron, a flow-matching generative model to improve predictions for disordered proteins.',
        'categories': ['biophysics'],
        'version': 1,
        'keep': True,
        'relevance_score': 85,
        'buckets': ['Protein Modeling & Bioinformatics', 'Drug Discovery & Compound Screening'],
        'why_it_matters': 'This work addresses a major limitation of current protein structure predictors like AlphaFold by improving the modeling of intrinsically disordered proteins (IDPs). Since IDPs are crucial in many diseases and are challenging drug targets, this could significantly advance structure-based drug discovery.',
        'summary': 'State-of-the-art protein structure predictors like AlphaFold perform poorly on intrinsically disordered proteins (IDPs), which are implicated in numerous diseases. This paper introduces PeptoneBench and PepTron, a flow-matching generative model trained with synthetic disordered ensembles, achieving performance comparable to computationally expensive simulation methods.',
        'code_urls': [],
        'dataset_urls': [],
        'arxiv_link': 'https://doi.org/10.1101/2025.10.18.680935',
        'pdf_link': 'https://www.biorxiv.org/content/10.1101/2025.10.18.680935v1.full.pdf',
        'in_top_picks': True
    },
    {
        'arxiv_id': '10.1101/2025.11.03.686348',
        'title': 'Himito: a Graph-based Toolkit for Mitochondrial Genome Analysis using Long Reads',
        'abstract': 'Understanding the genetic and epigenetic regulation of mitochondrial DNA (mtDNA) is essential for elucidating mechanisms of aging and disease. Himito provides superior, integrated analysis of mitochondrial genomes from long-read sequencing.',
        'categories': ['bioinformatics'],
        'version': 1,
        'keep': True,
        'relevance_score': 75,
        'buckets': ['Genomics & Computational Biology', 'Protein Modeling & Bioinformatics'],
        'why_it_matters': 'This toolkit provides a superior, integrated method for analyzing mitochondrial DNA from long-read sequencing, crucial for understanding aging and diseases linked to mitochondrial dysfunction. Validated on the large-scale \'All of Us\' dataset, it demonstrates real-world utility in identifying pathogenic variants.',
        'summary': 'Himito is a new graph-based bioinformatics toolkit for analyzing mitochondrial genomes using long-read sequencing data. It offers superior performance in variant calling and assembly, and enables integrated analysis of genetic and epigenetic modifications, as demonstrated on the large \'All of Us\' human dataset.',
        'code_urls': ['https://github.com/broadinstitute/Himito'],
        'dataset_urls': [],
        'arxiv_link': 'https://doi.org/10.1101/2025.11.03.686348',
        'pdf_link': 'https://www.biorxiv.org/content/10.1101/2025.11.03.686348v1.full.pdf',
        'in_top_picks': True
    },
    {
        'arxiv_id': '10.1101/2025.09.27.678895',
        'title': 'Multimodal Imaging and Logistic Weighted Cognitive Scores for Classification of MCI, AD, and FTD Subtypes',
        'abstract': 'Differentiating between mild cognitive impairment (MCI), Alzheimers disease (AD), and frontotemporal dementia (FTD) subtypes remains a clinical challenge. This study developed a model combining structural MRI and FDG-PET imaging with cognitive test scores.',
        'categories': ['neuroscience'],
        'version': 1,
        'keep': True,
        'relevance_score': 55,
        'buckets': ['AI Diagnostics & Medical Imaging', 'Neuroscience & Brain-Computer Interfaces'],
        'why_it_matters': 'This paper addresses the significant clinical challenge of differentiating between dementia subtypes like Alzheimer\'s and FTD, which often have overlapping symptoms. Its novelty lies in integrating cognitive test scores directly with multimodal neuroimaging data to potentially improve diagnostic precision in early stages.',
        'summary': 'This study developed a model to classify dementia subtypes (MCI, AD, FTD) by combining structural MRI and FDG-PET imaging features, weighted by cognitive scores from the ACE-III test. Using a Naive Bayes classifier on data from 100 participants, the model achieved moderate overall accuracy (68%).',
        'code_urls': [],
        'dataset_urls': [],
        'arxiv_link': 'https://doi.org/10.1101/2025.09.27.678895',
        'pdf_link': 'https://www.biorxiv.org/content/10.1101/2025.09.27.678895v1.full.pdf',
        'in_top_picks': True
    },
    {
        'arxiv_id': '10.1101/2025.11.04.686578',
        'title': 'Agent-based simulations of lung tumour evolution suggest that ongoing cell competition drives realistic clonal expansions',
        'abstract': 'Computational simulations of tumour evolution are increasingly used to infer the rules underlying cancer growth. This paper uses agent-based simulations to model 3D lung tumor growth with stringent competition for space.',
        'categories': ['cancer biology'],
        'version': 1,
        'keep': True,
        'relevance_score': 45,
        'buckets': ['Genomics & Computational Biology'],
        'why_it_matters': 'This paper demonstrates how agent-based simulations can be tailored to more accurately model the complex dynamics of tumor growth, specifically clonal expansion in lung cancer. This improved realism is a foundational step towards creating better in-silico models for studying cancer and potentially testing therapeutic strategies.',
        'summary': 'This paper uses agent-based simulations to model 3D lung tumor growth. The authors find that a model incorporating stringent competition for space best replicates the late subclonal expansions observed in real patient sequencing data, leading to more realistic estimates of driver mutation fitness.',
        'code_urls': [],
        'dataset_urls': [],
        'arxiv_link': 'https://doi.org/10.1101/2025.11.04.686578',
        'pdf_link': 'https://www.biorxiv.org/content/10.1101/2025.11.04.686578v1.full.pdf',
        'in_top_picks': False
    },
    {
        'arxiv_id': '10.1101/2025.10.28.685244',
        'title': 'Reversing transgene silencing via targeted chromatin editing',
        'abstract': 'Mammalian cell engineering offers the opportunity to develop next-generation biotechnologies. However, epigenetic silencing of transgenes hinders gene expression control. This paper shows that targeted DNA demethylation can effectively reactivate gene expression.',
        'categories': ['bioengineering'],
        'version': 1,
        'keep': True,
        'relevance_score': 55,
        'buckets': ['Genomics & Computational Biology'],
        'why_it_matters': 'This work provides a foundational bioengineering tool for controlling gene expression in mammalian cells, which is critical for developing stable cell lines for biomanufacturing and cell-based therapies. The methodology for reversing gene silencing has significant biotech potential.',
        'summary': 'This paper investigates the epigenetic silencing of transgenes in mammalian cells, a key challenge in biotechnology. Using chromatin editing and a computational model, the authors show that DNA methylation is the primary driver of silencing and demonstrate that targeted DNA demethylation can effectively reactivate gene expression.',
        'code_urls': [],
        'dataset_urls': [],
        'arxiv_link': 'https://doi.org/10.1101/2025.10.28.685244',
        'pdf_link': 'https://www.biorxiv.org/content/10.1101/2025.10.28.685244v1.full.pdf',
        'in_top_picks': False
    }
]

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Create renderer and email client
renderer = EmailRenderer(config)
email_client = ResendClient(
    api_key=os.getenv('RESEND_API_KEY'),
    config=config
)

# Organize papers
top_picks = [p for p in mock_papers if p.get('in_top_picks', False)]
buckets = {
    'AI Diagnostics & Medical Imaging': [p for p in mock_papers if 'AI Diagnostics & Medical Imaging' in p.get('buckets', [])],
    'Drug Discovery & Compound Screening': [p for p in mock_papers if 'Drug Discovery & Compound Screening' in p.get('buckets', [])],
    'Protein Modeling & Bioinformatics': [p for p in mock_papers if 'Protein Modeling & Bioinformatics' in p.get('buckets', [])],
    'Neuroscience & Brain-Computer Interfaces': [p for p in mock_papers if 'Neuroscience & Brain-Computer Interfaces' in p.get('buckets', [])],
    'Genomics & Computational Biology': [p for p in mock_papers if 'Genomics & Computational Biology' in p.get('buckets', [])]
}
also_noteworthy = []
filtered_out = []

# Render email
html = renderer.render(
    top_picks=top_picks,
    buckets=buckets,
    also_noteworthy=also_noteworthy,
    filtered_out=filtered_out,
    metadata={'total_papers': len(mock_papers)}
)

# Send email
subject = f"Bio Daily Research Digest - {datetime.now().strftime('%a, %b %d')} [Test Email]"
recipients = config['digest']['recipients']

success = email_client.send_digest(
    recipients=recipients,
    subject=subject,
    html_content=html
)

if success:
    print(f"✅ Test email sent successfully to {recipients}")
    print("📧 Email contains biomedical AI research papers:")
    print("   • Protein structure prediction (AlphaFold-related)")
    print("   • Mitochondrial genomics analysis")
    print("   • AI for dementia diagnosis (MRI/PET imaging)")
    print("   • Cancer tumor simulation")
    print("   • Gene expression control for biotech")
else:
    print("❌ Failed to send email")

# Also save to file for preview
with open('bio_digest_preview.html', 'w') as f:
    f.write(html)

print("📄 Preview saved to: bio_digest_preview.html")
