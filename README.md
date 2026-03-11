# Automated Auditorium Lighting System

AI-driven system that reads time-stamped play or event scripts and produces lighting cue sequences matching each scene's mood.

## Features

- 🎭 Multi-format script support: **.txt, .pdf, .docx**
- 🤖 ML-based emotion detection using DistilRoBERTa
- ⏱️ Automatic timestamp generation or extraction
- 📊 Comprehensive JSON output with metadata
- 🎨 Genre classification
- 🔄 Modular pipeline architecture

## Supported File Formats

| Format | Extension | Status | Notes |
|--------|-----------|--------|-------|
| Plain Text | `.txt` | ✅ Full Support | Best for manual scripts |
| PDF | `.pdf` | ✅ Full Support | Requires PyPDF2 |
| Word | `.docx` | ✅ Full Support | Requires python-docx |
| Legacy Word | `.doc` | ❌ Not Supported | Convert to .docx first |

## Installation
```bash
# Clone repository
git clone <repository-url>
cd Automated_Auditorium_Lighting

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install ALL dependencies (including PDF and DOCX support)
pip install -r requirements.txt

# OR install selectively:
# For text only:
pip install transformers torch

# For PDF support:
pip install transformers torch PyPDF2

# For DOCX support:
pip install transformers torch python-docx
```

## Quick Start
```bash
# Process a text file
python main.py data/raw_scripts/my_script.txt

# Process a PDF
python main.py data/raw_scripts/screenplay.pdf

# Process a Word document
python main.py data/raw_scripts/play.docx

# Specify custom output location
python main.py data/raw_scripts/my_script.pdf data/standardized_output/output.json
```

## File Format Examples

### Text File (.txt)
```
[00:00] SCENE 1 - INTERIOR CASTLE
Romeo enters the grand hall...
```

### PDF File (.pdf)
- Standard screenplay PDFs
- Exported scripts from Final Draft, Celtx, etc.
- Scanned scripts (text must be OCR'd)

### Word Document (.docx)
- Scripts formatted in Microsoft Word
- Google Docs exported as .docx
- LibreOffice Writer documents

## Troubleshooting

### PDF Issues
```bash
# If PDF extraction fails
pip install --upgrade PyPDF2

# Try alternative PDF library
pip install pypdf
```

### DOCX Issues
```bash
# If DOCX reading fails
pip install --upgrade python-docx
```

### Legacy .doc Files
Legacy `.doc` format is not supported. Convert to `.docx`:
- Open in Microsoft Word → Save As → .docx
- Use LibreOffice Writer → Save As → .docx
- Online converter: doc2docx.com

## Configuration

Edit `config.py` to customize:

- Speaking speed (WORDS_PER_MINUTE)
- Scene segmentation parameters
- Emotion detection thresholds
- Output formats

## Project Structure
```
Automated_Auditorium_Lighting/
├── data/
│   ├── raw_scripts/          # Input: .txt, .pdf, .docx
│   ├── cleaned_scripts/      # Intermediate cleaned data
│   ├── segmented_scripts/    # Intermediate segmented data
│   └── standardized_output/  # Final JSON outputs
├── pipeline/                 # Core processing modules
├── utils/                    # File I/O with format support
├── config.py                # Configuration settings
└── main.py                  # Main pipeline script
```

## Output Format

The pipeline produces JSON with:
```json
{
  "metadata": {
    "generated_at": "2026-01-27T...",
    "total_scenes": 10,
    "source_format": ".pdf",
    "format_detected": "screenplay",
    "emotion_distribution": {...}
  },
  "scenes": [...]
}
```

## Next Steps

This processed output can be used for:
1. Lighting cue generation (Phase 2)
2. DMX/Art-Net control
3. 3D visualization
4. Real-time hardware control

## License

[Your License]