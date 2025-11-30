# ShadowPen: Synergizing Human Strategy with Proactive Shadow Agent for XSS Testing

[![Paper](https://img.shields.io/badge/Paper-CSCWD%202025-blue)](https://github.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-yellow.svg)](https://www.python.org)

> **Official Repository** for the research paper:  
> *"ShadowPen: Synergizing Human Strategy with Proactive Shadow Agent for XSS Testing"*  
> Submitted to **CSCWD 2025** (International Conference on Computer Supported Cooperative Work in Design)

---

## 📖 Overview

**ShadowPen** is a next-generation intelligent XSS (Cross-Site Scripting) vulnerability detection system that seamlessly integrates **human expertise** with **AI-driven automation**. By introducing a **Proactive Shadow Agent**, ShadowPen enables security researchers to perform deep, context-aware vulnerability testing while significantly reducing manual effort.

### Key Innovations

- **🤖 Proactive Mixed-Initiative Shadow Agent**: An LLM-powered assistant that proactively suggests attack surfaces, mutation strategies, and provides real-time guidance.
- **🕷️ State-Aware Intelligent Crawler**: Combines static (GoSpider, Katana) and dynamic analysis (Playwright) for comprehensive attack surface discovery.
- **🧬 LLM-Driven Mutation Engine**: Generates advanced payload variants using encoding, obfuscation, polyglots, and WAF evasion techniques.
- **🎯 Semantic Interaction Simulation**: Identifies and triggers hidden injection points through intelligent DOM event simulation.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│              User Interface (Vue 3)              │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│           Backend (FastAPI + Redis)             │
│  ┌───────────────────┬──────────────────────┐  │
│  │  Crawler Engine   │  ShadowModel Engine  │  │
│  │  • GoSpider       │  • Attack Surface    │  │
│  │  • Katana         │    Analysis (LLM)    │  │
│  │  • Playwright     │  • Payload Mutation  │  │
│  │  • CDP Protocol   │  • Chat Assistant    │  │
│  └───────────────────┴──────────────────────┘  │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────▼───────────┐
        │   Target Web Apps     │
        │  (Benchmark Suite)    │
        └───────────────────────┘
```

---

## 📦 Repository Structure

```
collabXSS/
├── ShadowPen/                      # Main System
│   ├── backend/                    # FastAPI Backend
│   │   ├── crawler_engine/         # Hybrid Crawler Module
│   │   │   ├── static_scan.py      # GoSpider + Katana Integration
│   │   │   ├── dynamic_scan.py     # Playwright Automation
│   │   │   ├── dom_analyzer.py     # Form & Input Detection
│   │   │   └── traffic_interceptor.py  # Request Capture
│   │   ├── shadowmodel_engine/     # LLM Core
│   │   │   ├── mutation.py         # Payload Generation
│   │   │   ├── surface_analysis.py # Attack Surface Ranking
│   │   │   └── chat.py             # Proactive Assistant
│   │   ├── prompts.py              # LLM Prompt Engineering
│   │   ├── app.py                  # FastAPI Server
│   │   └── requirements.txt
│   ├── frontend/                   # Vue 3 + Vite
│   │   ├── src/
│   │   │   ├── components/         # 4-Step Testing UI
│   │   │   │   ├── Step1_UrlInput.vue
│   │   │   │   ├── Step2_Crawling.vue
│   │   │   │   ├── Step3_InjectionPoints.vue
│   │   │   │   └── Step4_Testing.vue
│   │   │   └── ChatDrawer.vue      # Shadow Agent Interface
│   │   └── package.json
│   └── docker-compose.yml          # Full Stack Deployment
│
├── django_wiki/                    # Benchmark App #1 (Django + SQLite)
├── flask_techNews/                 # Benchmark App #2 (Flask + Python)
├── go_ticket/                      # Benchmark App #3 (Go + Templates)
├── java_employee/                  # Benchmark App #4 (Java + Spring)
├── node_feedback/                  # Benchmark App #5 (Node.js + Express)
├── php_blog/                       # Benchmark App #6 (PHP + MySQL)
├── react_fastapi_social/           # Benchmark App #7 (React + FastAPI)
├── react_node_task/                # Benchmark App #8 (React + Node.js)
├── ruby_gallery/                   # Benchmark App #9 (Ruby on Rails)
└── vue_spring_shop/                # Benchmark App #10 (Vue + Spring Boot)
```

---

## 🎯 Benchmark Suite

This repository includes **10 diverse web applications** spanning multiple technology stacks, each containing intentionally injected XSS vulnerabilities for evaluation purposes:

| Application | Tech Stack | Vulnerability Types |
|------------|-----------|---------------------|
| **django_wiki** | Django + SQLite | Stored XSS in article content |
| **flask_techNews** | Flask + Jinja2 | Reflected XSS in search |
| **go_ticket** | Go + Templates | DOM-based XSS in URL params |
| **java_employee** | Spring Boot + Thymeleaf | Stored XSS in employee profiles |
| **node_feedback** | Express + EJS | Reflected XSS in feedback form |
| **php_blog** | PHP + MySQL | Multi-context XSS (comments) |
| **react_fastapi_social** | React + FastAPI | JSON-based XSS in API |
| **react_node_task** | React + Node.js | Client-side XSS in task list |
| **ruby_gallery** | Rails + ERB | Stored XSS in image descriptions |
| **vue_spring_shop** | Vue 3 + Spring | Parameter pollution XSS |

> ⚠️ **Disclaimer**: These applications are for **research and educational purposes only**. Do not deploy in production environments.

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.9+
- Node.js 16+
- OpenAI API Key (for LLM features)

### Installation

#### Option 1: Docker (Recommended)

```bash
cd ShadowPen
cp .env.example .env  # Configure your OpenAI API key
docker compose up -d
```

Access the system at:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/docs

#### Option 2: Manual Setup

**Backend:**
```bash
cd ShadowPen/backend
pip install -r requirements.txt
# Install external tools
go install -v github.com/projectdiscovery/katana/cmd/katana@latest
go install github.com/jaeles-project/gospider@latest
playwright install

# Configure environment
export OPENAI_API_KEY="your-key-here"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"

# Start server
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
cd ShadowPen/frontend
npm install
npm run dev
```

### Testing Workflow

1. **Start a Benchmark App** (e.g., Flask TechNews):
   ```bash
   cd flask_techNews
   python app.py  # Starts on port 5000
   ```

2. **Launch ShadowPen**:
   - Enter target URL: `http://localhost:5000`
   - Step 1: URL Configuration
   - Step 2: Automated Crawling (GoSpider → Katana → Playwright)
   - Step 3: LLM Attack Surface Analysis
   - Step 4: Mutation Testing with Shadow Agent guidance

3. **Engage the Shadow Agent**:
   - Ask: *"Which parameters look most vulnerable?"*
   - Request: *"Generate polyglot payloads for the search field"*
   - Get proactive suggestions during testing

---

## 🔬 Core Features

### 1. Hybrid Crawling Pipeline

```python
# Sequential Architecture
Static Scanners (GoSpider + Katana)  
    ↓ Asset Discovery
Dynamic Analysis (Playwright + CDP)  
    ↓ State-Aware Traversal
DOM Interaction Engine  
    ↓ Event Simulation
Traffic Interceptor  
    ↓ Parameter Extraction
→ Attack Surface Database
```

**Technologies:**
- **GoSpider**: Fast link extraction and asset mapping
- **Katana**: Headless crawling with JavaScript rendering
- **Playwright**: Cross-browser automation (Chromium CDP)
- **Custom DOM Analyzer**: Form field detection, input discovery

### 2. LLM-Driven Attack Surface Analysis

The Shadow Agent analyzes crawled surfaces using a **conservative filtering strategy**:

**Retention Criteria:**
- ✅ Any URL with query parameters
- ✅ POST/PUT/DELETE endpoints
- ✅ JSON APIs and form submissions
- ✅ Parameters matching XSS vectors: `q`, `search`, `callback`, `url`, `redirect`, `name`, `email`, `comment`

**Risk Scoring (0-10):**
- Base: 3 points
- +3: POST/PUT/DELETE methods
- +2: High-value parameter names
- +2: JSON/Multipart content
- +2: Deep interaction detected (depth_level > 0)
- +1: Path parameters

### 3. Advanced Mutation Engine

**Techniques:**
- **Encoding**: Double URL encoding, HTML entities (decimal/hex), Unicode escapes
- **Obfuscation**: Case variation, whitespace manipulation, null bytes
- **Polyglots**: Multi-context payloads (`<svg/onload=alert(1)>`)
- **Alternative Tags**: `<details>`, `<marquee>`, `ontoggle`, `onanimationstart`

**Example Mutation Workflow:**
```javascript
User Payload: <script>alert(1)</script>

LLM-Generated Variants:
1. "><svg/onload=alert(1)>
2. %3Cscript%3Ealert%281%29%3C%2Fscript%3E
3. <img src=x onerror=&#97;&#108;&#101;&#114;&#116;(1)>
```

### 4. Proactive Shadow Agent

**Capabilities:**
- **Contextual Suggestions**: "This `callback` parameter might allow JSONP hijacking"
- **Strategic Guidance**: "Try breaking out of the JSON context with `\"`"
- **Real-time Assistance**: Interactive chat during entire testing workflow
- **Payload Explanation**: "This uses SVG to bypass `<script>` tag filters"

---

## 📊 Research Contribution

This work addresses critical gaps in automated XSS testing:

1. **Human-AI Synergy**: Unlike fully automated tools (e.g., ZAP, Burp Scanner), ShadowPen keeps humans in the loop while reducing cognitive load through proactive AI assistance.

2. **State-Aware Discovery**: Combines static and dynamic analysis to uncover injection points hidden behind JavaScript events and AJAX workflows.

3. **Intelligent Prioritization**: LLM-based risk scoring reduces false positives and focuses testing on high-value targets.

4. **Adaptive Mutation**: Context-aware payload generation that considers WAF signatures, CSP policies, and encoding requirements.

---

## 🧪 Evaluation

### Experimental Setup

- **Benchmark**: 10 diverse web applications (see table above)
- **Baselines**: OWASP ZAP, Burp Suite Community, Manual Testing
- **Metrics**:
  - **Coverage**: Percentage of injection points discovered
  - **Precision**: Ratio of true positives to total findings
  - **Efficiency**: Time to discovery (user + system)
  - **User Study**: Task completion rate, cognitive load (NASA-TLX)

### Preliminary Results

*(Results to be included after full evaluation)*

---

## 📝 Citation

If you use ShadowPen or this benchmark suite in your research, please cite:

```bibtex
@inproceedings{shadowpen2025,
  title={ShadowPen: Synergizing Human Strategy with Proactive Shadow Agent for XSS Testing},
  author={[Your Name]},
  booktitle={Proceedings of the 29th International Conference on Computer Supported Cooperative Work in Design (CSCWD)},
  year={2025},
  organization={IEEE}
}
```

---

## 🛡️ Responsible Disclosure

- This tool is designed for **authorized security testing only**.
- The benchmark applications contain **intentional vulnerabilities** and must **NOT** be deployed publicly.
- Users are responsible for compliance with local laws and regulations.

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas of Interest:**
- Additional benchmark applications in other tech stacks (Rust, Elixir, etc.)
- Enhanced mutation strategies (e.g., machine learning-based generation)
- Integration with other LLM providers (Anthropic Claude, Google Gemini)

---

## 📧 Citation

If you use this repo in your research, please cite:

```bibtex
@inproceedings{shadowpen2025,
  title={ShadowPen: Synergizing Human Strategy with Proactive Shadow Agent for XSS Testing},
  author={[Jianguo Wu, Yakai Li, Kexin Hao, Zhaojing Yuan, Luping Ma, Weijuan Zhang, Yi Su, Qingjia Huang
]},
  booktitle={Proceedings of the 29th International Conference on Computer Supported Cooperative Work in Design (CSCWD)},
  year={2026},
  note={Submitted}
}
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **OWASP** for XSS testing methodologies
- **ProjectDiscovery** (Katana) and **Jaeles Project** (GoSpider) for open-source crawlers
- **OpenAI** for GPT API infrastructure
- **CSCWD 2025** reviewers and organizers

---

**⚡ Built with ❤️ for the security research community**
