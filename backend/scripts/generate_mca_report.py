"""
Script to generate Orion MCA Final Project Report (.docx)
Adhering strictly to Calicut University / St. Joseph's College guidelines.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_element(name):
    return OxmlElement(name)

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="D3D3D3", sz="4"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:bottom w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideH w:val="single" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'<w:insideV w:val="none"/>'
        f'<w:left w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_report():
    output_dir = os.path.join("docs", "report")
    os.makedirs(output_dir, exist_ok=True)
    doc_path = os.path.join(output_dir, "Orion_MCA_Final_Project_Report.docx")

    doc = Document()

    # Section Margins: A4, Left 1.5", Right/Top/Bottom 1.0"
    for section in doc.sections:
        section.page_width = Inches(8.27)
        section.page_height = Inches(11.69)
        section.left_margin = Inches(1.5)
        section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)

    # Styles Setup
    normal_style = doc.styles['Normal']
    normal_font = normal_style.font
    normal_font.name = 'Times New Roman'
    normal_font.size = Pt(12)
    normal_font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.5
    normal_style.paragraph_format.space_after = Pt(6)
    normal_style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def add_title(text, size=18, bold=True, space_before=0, space_after=12, align=WD_ALIGN_PARAGRAPH.CENTER):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.2
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h1(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(10)
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h2(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_h3(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.keep_with_next = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0, 0, 0)
        return p

    def add_p(text, bold_prefix="", italic=False):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(6)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
            r_pre.font.bold = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        run.font.italic = italic
        return p

    def add_bullet(text, bold_prefix=""):
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.space_after = Pt(4)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.font.name = 'Times New Roman'
            r_pre.font.size = Pt(12)
            r_pre.font.bold = True
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
        return p

    def add_image_figure(img_path, caption_text, width=Inches(5.7)):
        if os.path.exists(img_path):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run()
            run.add_picture(img_path, width=width)
            
            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_before = Pt(2)
            p_cap.paragraph_format.space_after = Pt(14)
            r_cap = p_cap.add_run(caption_text)
            r_cap.font.name = 'Times New Roman'
            r_cap.font.size = Pt(11)
            r_cap.font.bold = True
            r_cap.font.italic = True
        else:
            p_missing = doc.add_paragraph()
            p_missing.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p_missing.add_run(f"[{caption_text} - Image file not found: {img_path}]")
            r.font.italic = True

    # =========================================================================
    # 1. COVER PAGE / TITLE PAGE
    # =========================================================================
    add_title("ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE", size=20, bold=True, space_before=40, space_after=24)
    add_title("A PROJECT REPORT", size=14, bold=True, space_after=8)
    add_title("Submitted in partial fulfillment of the requirement for the award of the degree of", size=12, bold=False, space_after=8)
    add_title("MASTER OF COMPUTER APPLICATIONS", size=15, bold=True, space_after=32)

    add_title("Submitted by", size=12, bold=False, space_after=6)
    add_title("ATHUL RAJ A K", size=14, bold=True, space_after=4)
    add_title("(Reg. No: SJC24MCA015)", size=12, bold=True, space_after=36)

    add_title("Under the Guidance of", size=12, bold=False, space_after=6)
    add_title("Dr. [GUIDE NAME], Ph.D.", size=13, bold=True, space_after=4)
    add_title("Associate Professor, Dept. of Computer Applications", size=11, bold=False, space_after=50)

    add_title("DEPARTMENT OF COMPUTER APPLICATIONS", size=14, bold=True, space_after=6)
    add_title("ST. JOSEPH'S COLLEGE (AUTONOMOUS), DEVAGIRI, CALICUT", size=13, bold=True, space_after=4)
    add_title("AFFILIATED TO THE UNIVERSITY OF CALICUT", size=12, bold=False, space_after=8)
    add_title("MAY 2026", size=12, bold=True, space_after=0)

    doc.add_page_break()

    # =========================================================================
    # 2. CERTIFICATE
    # =========================================================================
    add_title("ST. JOSEPH'S COLLEGE (AUTONOMOUS), DEVAGIRI", size=15, bold=True, space_before=10, space_after=4)
    add_title("DEPARTMENT OF COMPUTER APPLICATIONS", size=13, bold=True, space_after=24)
    add_title("CERTIFICATE", size=16, bold=True, space_after=28)

    add_p(
        "This is to certify that the project report titled \"ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE\" "
        "is a bona fide record of the work carried out by ATHUL RAJ A K (Reg. No: SJC24MCA015) in partial fulfillment of "
        "the requirements for the award of the degree of Master of Computer Applications affiliated to the University of Calicut "
        "during the academic year 2024–2026."
    )
    add_p(
        "The project work has been carried out under our supervision and guidance, and no part thereof has been submitted "
        "for the award of any other degree, diploma, or fellowship."
    )

    # Signatures
    p_sig = doc.add_paragraph()
    p_sig.paragraph_format.space_before = Pt(80)
    p_sig.paragraph_format.space_after = Pt(50)
    r_sig = p_sig.add_run(
        "Project Guide                                                  Head of the Department\n"
        "[Guide Name], Associate Professor                               [HOD Name], Professor & HOD\n"
        "Dept. of Computer Applications                                 Dept. of Computer Applications"
    )
    r_sig.font.name = 'Times New Roman'
    r_sig.font.size = Pt(11)

    p_eval = doc.add_paragraph()
    p_eval.paragraph_format.space_before = Pt(40)
    r_eval = p_eval.add_run(
        "Submitted for the Viva-Voce Examination held on: ____________________\n\n"
        "Internal Examiner: ____________________          External Examiner: ____________________"
    )
    r_eval.font.name = 'Times New Roman'
    r_eval.font.size = Pt(11)

    doc.add_page_break()

    # =========================================================================
    # 3. DECLARATION
    # =========================================================================
    add_title("DECLARATION", size=16, bold=True, space_before=10, space_after=28)
    add_p(
        "I hereby declare that the project entitled \"ORION: AI-POWERED REQUIREMENTS TRACEABILITY MATRIX ENGINE\" "
        "submitted to the Department of Computer Applications, St. Joseph's College (Autonomous), Devagiri, Calicut, "
        "affiliated to the University of Calicut, in partial fulfillment of the requirements for the award of the degree "
        "of Master of Computer Applications, is an authentic record of original project work carried out by me under the "
        "supervision of [Guide Name], Department of Computer Applications."
    )
    add_p(
        "I further declare that this report has not previously formed the basis for the award of any degree, diploma, "
        "associateship, fellowship, or other similar title to any candidate of any university or institution."
    )

    p_dec_sig = doc.add_paragraph()
    p_dec_sig.paragraph_format.space_before = Pt(70)
    r_dec_sig = p_dec_sig.add_run(
        "Place: Calicut\n"
        "Date:  ____________________                                    ATHUL RAJ A K\n"
        "                                                               (Reg. No: SJC24MCA015)"
    )
    r_dec_sig.font.name = 'Times New Roman'
    r_dec_sig.font.size = Pt(11)

    doc.add_page_break()

    # =========================================================================
    # 4. ACKNOWLEDGEMENT
    # =========================================================================
    add_title("ACKNOWLEDGEMENT", size=16, bold=True, space_before=10, space_after=28)
    add_p(
        "First and foremost, I praise God Almighty for His immense grace, wisdom, and blessings that sustained me throughout "
        "the completion of this academic project."
    )
    add_p(
        "I express my profound sense of gratitude to Dr. Bobby Jose, Principal, St. Joseph's College (Autonomous), Devagiri, "
        "Calicut, for providing the necessary administrative and computational infrastructure to undertake this work."
    )
    add_p(
        "I extend my sincere gratitude to [HOD Name], Head of the Department of Computer Applications, for continuous "
        "encouragement and professional guidance throughout the curriculum."
    )
    add_p(
        "I am deeply indebted to my project supervisor, [Guide Name], Associate Professor, Department of Computer Applications, "
        "for insightful technical reviews, invaluable guidance, and patient mentoring during all phases of development."
    )
    add_p(
        "Finally, I express my heartfelt love and indebtedness to my parents, family members, and peers for their continuous "
        "moral support and motivation throughout my academic endeavors."
    )

    doc.add_page_break()

    # =========================================================================
    # 5. SYNOPSIS
    # =========================================================================
    add_title("SYNOPSIS", size=16, bold=True, space_before=10, space_after=28)
    add_p(
        "Orion is an automated, AI-driven Requirements Traceability Matrix (RTM) governance platform engineered to eliminate "
        "silent specification drift between agile product backlogs and continuous integration (CI/CD) test suites. Modern agile "
        "development pipelines suffer from divergence where code assertions fail to validate quantitative acceptance criteria "
        "defined in Jira issues. Traditional verification relies on manual audit reviews or rigid keyword matching that fails "
        "to identify subtle semantic and structural regressions."
    )
    add_p(
        "Orion resolves this by implementing a dual-sided hybrid evaluation pipeline combining a 384-dimensional dense semantic "
        "embedding model (BAAI/bge-small-en-v1.5) running via ONNX Runtime with a deterministic Python Abstract Syntax Tree (AST) "
        "structural parser. The platform continuously synchronizes Atlassian Document Format (ADF) user stories from Jira Cloud, "
        "converts test files via AST extraction into structured assertion syntax, stores high-dimensional embeddings using "
        "PostgreSQL pgvector, and computes a composite compliance score:"
    )
    add_p(
        "S_hybrid = 0.6 · S_sem(Req, Test) + 0.4 · S_struct(Req, Test)",
        italic=True
    )
    add_p(
        "When structural divergence or semantic degradation is identified, Orion generates natural language explanations using an "
        "on-premise Large Language Model (Meta Llama 3.1 8B via Ollama) and automatically registers GitHub Check Run annotations to "
        "block pull request merges. A real-time executive dashboard built with React and Vite visualizes the complete traceability "
        "matrix, surfaces sensitivity threshold controls, and enforces Role-Based Access Control (RBAC)."
    )

    doc.add_page_break()

    # =========================================================================
    # 6. TABLE OF CONTENTS
    # =========================================================================
    add_title("TABLE OF CONTENTS", size=16, bold=True, space_before=10, space_after=28)
    
    toc_data = [
        ("CHAPTER I: INTRODUCTION", "1"),
        ("  1.1 Orion - An Overview", "1"),
        ("  1.2 Mission of the Project", "2"),
        ("  1.3 Background Study", "3"),
        ("    1.3.1 Study on Existing System", "3"),
        ("    1.3.2 Disadvantages of Existing System", "4"),
        ("CHAPTER II: SYSTEM ANALYSIS", "5"),
        ("  2.1 Study on Proposed System", "5"),
        ("    2.1.1 Advantages of Proposed System", "5"),
        ("  2.2 User Requirement Specification", "6"),
        ("  2.3 Software Requirement Specification", "8"),
        ("  2.4 Feasibility Study", "9"),
        ("    2.4.1 Technical Feasibility", "9"),
        ("    2.4.2 Economic Feasibility", "10"),
        ("    2.4.3 Operational Feasibility", "10"),
        ("  2.5 System Specification", "11"),
        ("    2.5.1 Hardware Specification", "11"),
        ("    2.5.2 Software Specification", "11"),
        ("    2.5.3 Technology Used", "12"),
        ("  2.6 Cost Estimation and Scheduling", "13"),
        ("    2.6.1 Cost Estimation", "13"),
        ("    2.6.2 Scheduling (Agile Iterations)", "14"),
        ("CHAPTER III: DESIGN AND DEVELOPMENT PROCESS", "15"),
        ("  3.1 Fundamental Design Concepts", "15"),
        ("  3.2 Design Notations & Diagrams", "16"),
        ("    3.2.1 Data Flow Diagrams (Context Level 0, Level 1, Level 2)", "16"),
        ("    3.2.2 Use Case Modeling (Role-Based Interactions)", "22"),
        ("  3.3 Design Process", "24"),
        ("    3.3.1 Database Schema Design", "24"),
        ("    3.3.2 Normalization (1NF, 2NF, 3NF)", "27"),
        ("    3.3.3 Input Design", "28"),
        ("    3.3.4 Output Design", "29"),
        ("  3.4 Development Approach (Agile Sprints)", "30"),
        ("CHAPTER IV: CODING", "31"),
        ("  4.1 Frontend Architecture (React / Vite / RBAC)", "31"),
        ("  4.2 Backend Architecture (FastAPI / SQLAlchemy / Async I/O)", "33"),
        ("  4.3 AI & Parser Subsystems (BGE-Small / AST / Ollama)", "35"),
        ("CHAPTER V: TESTING AND IMPLEMENTATION", "37"),
        ("  5.1 Testing Methodologies", "37"),
        ("    5.1.1 Unit Testing", "37"),
        ("    5.1.2 Integration Testing", "38"),
        ("    5.1.3 Validation Testing", "38"),
        ("    5.1.4 Test Cases and Results Chart", "39"),
        ("  5.2 Quality Assurance & Policies", "41"),
        ("    5.2.1 Generic Risk Analysis", "41"),
        ("  5.3 System Implementation Procedures", "42"),
        ("  5.4 System Maintenance", "43"),
        ("CHAPTER VI: CONCLUSION", "44"),
        ("  6.1 Conclusion", "44"),
        ("  6.2 Scope for Further Enhancement", "45"),
        ("  6.3 Bibliography", "46"),
        ("ANNEXURE - A: MAJOR INPUT AND OUTPUT SCREENS", "47"),
        ("ANNEXURE - B: TABLE OF ABBREVIATIONS", "49")
    ]

    toc_table = doc.add_table(rows=len(toc_data), cols=2)
    toc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(toc_table, "FFFFFF", "0")
    
    for i, (title, page) in enumerate(toc_data):
        row = toc_table.rows[i]
        c1, c2 = row.cells[0], row.cells[1]
        c1.width = Inches(5.8)
        c2.width = Inches(0.8)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.line_spacing = 1.3
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(title)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)
        if title.startswith("CHAPTER") or title.startswith("ANNEXURE"):
            r1.font.bold = True
            
        p2 = c2.paragraphs[0]
        p2.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p2.paragraph_format.line_spacing = 1.3
        p2.paragraph_format.space_after = Pt(2)
        r2 = p2.add_run(page)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER I: INTRODUCTION
    # =========================================================================
    add_h1("CHAPTER I: INTRODUCTION")
    
    add_h2("1.1 ORION - AN OVERVIEW")
    add_p(
        "Orion is an automated software quality engineering and compliance governance platform designed to bridge the operational "
        "divide between agile product management repositories and automated continuous integration (CI/CD) pipelines. In modern "
        "enterprise software development, high development velocity frequently leads to 'silent specification drift'—a condition "
        "where test suites pass green in automated builds while failing to validate actual quantitative business acceptance criteria."
    )
    add_p(
        "By replacing manual spreadsheets with real-time semantic analysis and code Abstract Syntax Tree (AST) inspection, Orion "
        "delivers an automated, deterministic Requirements Traceability Matrix (RTM). The platform connects to Jira Cloud via "
        "webhook listeners and REST APIs to ingest user stories and acceptance criteria, while simultaneously monitoring GitHub "
        "repositories for pull request events modifying test suites. It evaluates requirement-test alignment using a dual-sided "
        "hybrid scoring engine and enforces quality gating directly within pull request merge checks."
    )

    add_h2("1.2 MISSION OF THE PROJECT")
    add_p(
        "The primary mission of Orion is to establish continuous, deterministic software traceability that prevents unverified "
        "or regressed code from entering production environments. Specific project objectives include:"
    )
    add_bullet("Parse semi-structured acceptance criteria from Jira issues into machine-evaluable quantitative constraints.", "1. Constraint Extraction: ")
    add_bullet("Inspect Python test code directly via Abstract Syntax Trees to verify assertion targets, operators, and parameters without executing unsafe scripts.", "2. Deterministic AST Analysis: ")
    add_bullet("Synthesize semantic vector embeddings (0.6 weight) with AST structural assertion matches (0.4 weight) to generate mathematically grounded compliance verdicts.", "3. Hybrid Dual-Scoring: ")
    add_bullet("Enforce automated CI/CD gating using native GitHub Check Runs with exact line-level code annotations.", "4. Automated Quality Gating: ")
    add_bullet("Deliver local, privacy-preserving Explainable AI (XAI) root-cause summaries using an on-premise Meta Llama 3.1 8B model.", "5. Localized XAI Verbalization: ")

    add_h2("1.3 BACKGROUND STUDY")
    add_p(
        "Requirements Traceability is a mandatory engineering standard in safety-critical, financial, and enterprise software "
        "(ISO/IEC/IEEE 29148:2018). In conventional software lifecycles, RTMs are constructed manually using spreadsheets or static "
        "wiki tables. As development cycles accelerate through automated CI/CD pipelines, manual traceability matrices become "
        "obsolete within days of release."
    )

    add_h3("1.3.1 Study on Existing System")
    add_bullet("Traditional test management tools (e.g., Xray, Zephyr) require QA engineers to manually associate test case IDs with Jira tickets. They provide no automated verification of the test function's internal assertion logic.", "1. Manual Jira Test Management Plugins: ")
    add_bullet("Static analysis tools (e.g., SonarQube, Ruff) measure line and branch coverage percentages but cannot assess semantic correctness or verify whether asserted thresholds match business requirements.", "2. Static Linters and Coverage Profilers: ")
    add_bullet("Modern generative AI evaluation tools rely on third-party cloud APIs (e.g., OpenAI GPT-4). They introduce latency (2-5s per test), incur token costs, suffer from non-deterministic hallucinations, and expose proprietary code.", "3. Cloud-Hosted LLM Code Reviewers: ")

    add_h3("1.3.2 Disadvantages of Existing System")
    add_bullet("Engineering teams spend extensive billable hours manually compiling traceability documentation prior to release audits.", "• High Labor Overhead: ")
    add_bullet("A test suite can report 100% line coverage while asserting incorrect thresholds (e.g., asserting response_time <= 500ms when requirement mandates <= 200ms).", "• False Sense of Security: ")
    add_bullet("Cloud-hosted AI evaluation exposes internal Jira backlogs and source code to third-party endpoints, violating data sovereignty policies.", "• Intellectual Property Risks: ")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER II: SYSTEM ANALYSIS
    # =========================================================================
    add_h1("CHAPTER II: SYSTEM ANALYSIS")

    add_h2("2.1 STUDY ON PROPOSED SYSTEM")
    add_p(
        "The proposed Orion platform introduces a closed-loop, deterministic traceability architecture. By integrating directly into "
        "the developer's native version control and issue tracking systems, Orion evaluates every test file modification as part of the "
        "standard pull request workflow."
    )

    add_h3("2.1.1 Advantages of Proposed System")
    add_bullet("Extracts comparators, operands, and values directly from Python AST nodes, eliminating prompt indeterminism.", "1. Deterministic AST Verification: ")
    add_bullet("Utilizes BGE-Small (ONNX Runtime) and Llama 3.1 8B (Ollama) locally, ensuring zero cloud API costs and complete data privacy.", "2. Local Edge Inference: ")
    add_bullet("Automatically registers GitHub Check Runs with precise line-level failure annotations, blocking non-compliant pull requests.", "3. Native CI/CD Gating: ")
    add_bullet("Stores high-dimensional vectors in PostgreSQL pgvector alongside immutable audit logs, providing complete compliance verification.", "4. Unified Relational Storage: ")

    add_h2("2.2 USER REQUIREMENT SPECIFICATION")
    add_p("The system enforces strict Role-Based Access Control (RBAC) across two core human actors and one automated service actor:")
    
    add_h3("1. QA Lead / System Administrator")
    add_bullet("Authenticate via the enterprise session gate under administrative privileges.", "• Authentication: ")
    add_bullet("Inspect the comprehensive RTM matrix across all sprint user stories and test cases.", "• Traceability Inspection: ")
    add_bullet("Adjust global sensitivity parameters (tau_sem, tau_struct) via dynamic range sliders.", "• Policy Configuration: ")
    add_bullet("Perform authoritative manual risk score overrides with mandatory justification logging.", "• Manual Override: ")
    add_bullet("Execute simulation runs and inspect similarity distribution heatmaps.", "• Simulation & Analytics: ")

    add_h3("2. Software Developer")
    add_bullet("Login under Developer boundaries (threshold sliders and override buttons locked).", "• Authenticated Access: ")
    add_bullet("Tag test functions using standardized @traces(\"REQ-ID\") decorator syntax.", "• Code Tagging: ")
    add_bullet("Inspect requirement mappings, extracted AST assertion operands, and coverage verdicts.", "• Evidence Review: ")
    add_bullet("Read local Ollama XAI natural language gap rationales for drifted requirements.", "• Diagnostic Inspection: ")
    add_bullet("Trigger automated pull request check runs to validate branch compliance before merging.", "• Merge Validation: ")

    add_h3("3. CI Service Actor (Automated Engine)")
    add_bullet("Ingests webhooks from Jira Cloud and GitHub App using HMAC SHA-256 signature verification.", "• Webhook Processing: ")
    add_bullet("Executes background vector embeddings and AST comparisons.", "• Continuous Evaluation: ")
    add_bullet("Posts Check Runs to GitHub and syncs traceability status comments back to Jira.", "• Bidirectional Sync: ")

    add_h2("2.3 SOFTWARE REQUIREMENT SPECIFICATION")
    add_bullet("Windows 11 (64-bit) / Ubuntu 22.04 LTS", "• Operating System: ")
    add_bullet("Python 3.11+ (Backend Engine), Node.js v20+ (Frontend Dashboard)", "• Runtime Environments: ")
    add_bullet("FastAPI 0.115+ (Asynchronous ASGI Framework)", "• Backend Framework: ")
    add_bullet("PostgreSQL 16 with pgvector extension enabled", "• Database Engine: ")
    add_bullet("SQLAlchemy 2.0 (Asyncpg driver) with Alembic migration control", "• ORM Layer: ")
    add_bullet("BAAI/bge-small-en-v1.5 (384-dimensional dense embeddings via ONNX Runtime)", "• Embedding Model: ")
    add_bullet("Meta Llama 3.1 8B executed via local Ollama daemon", "• Local LLM Engine: ")
    add_bullet("React 18, Vite, Vanilla CSS Design System with Dark Theme tokens", "• Frontend Stack: ")

    add_h2("2.4 FEASIBILITY STUDY")
    add_p(
        "A comprehensive feasibility study was conducted to evaluate the viability, cost-efficiency, and operational readiness of Orion:"
    )
    add_bullet("The local embedding model (bge-small-en-v1.5) operates within 130MB of RAM and executes inference in under 30ms per requirement. The Python AST module is built into the standard library. PostgreSQL pgvector supports efficient HNSW indexing. Technical feasibility is fully confirmed on standard developer workstations.", "1. Technical Feasibility: ")
    add_bullet("By utilizing open-source models running on local hardware, Orion eliminates monthly LLM API token subscriptions. The software stack (FastAPI, React, PostgreSQL, Ollama) is entirely free and open-source.", "2. Economic Feasibility: ")
    add_bullet("Developers write standard pytest or unittest code, adding only the @traces decorator. Automated feedback is delivered inside GitHub PRs, requiring zero disruption to existing agile development habits.", "3. Operational Feasibility: ")

    add_h2("2.5 SYSTEM SPECIFICATION")
    add_h3("2.5.1 Hardware Specification")
    add_bullet("Intel Core i5 / AMD Ryzen 5 or higher (minimum 8 logical cores)", "• Processor: ")
    add_bullet("16 GB DDR4/DDR5 RAM (minimum 8 GB for lightweight CPU mode)", "• Memory: ")
    add_bullet("256 GB NVMe SSD (minimum 5 GB dedicated for pgvector storage and model weights)", "• Storage: ")
    add_bullet("Optional NVIDIA RTX GPU with CUDA 12 support (CPU fallback template engine available)", "• Acceleration: ")

    add_h3("2.5.2 Software Specification")
    add_bullet("Python 3.11, JavaScript (ES6+ / React JSX)", "• Programming Languages: ")
    add_bullet("Uvicorn (ASGI Application Server)", "• Application Server: ")
    add_bullet("Visual Studio Code / Antigravity IDE", "• Development Environment: ")
    add_bullet("pgAdmin 4, psql CLI", "• Database Tooling: ")
    add_bullet("Git 2.40+, GitHub Cloud Platform", "• Version Control: ")

    add_h2("2.6 COST ESTIMATION AND SCHEDULING")
    add_p(
        "Cost estimation for the Orion platform reflects an open-source development model utilizing existing academic laboratory hardware:"
    )
    add_bullet("Developer Workstation Hardware: ₹85,000", "• ")
    add_bullet("Software Tools & Licenses (Open Source): ₹0", "• ")
    add_bullet("Cloud API & Token Ingestion Fees: ₹0", "• ")
    add_bullet("Domain, SSL & Webhook Tunneling Infrastructure: ₹3,500", "• ")
    add_bullet("Total Development Expenditure: ₹88,500", "• ")

    add_p("The project followed an iterative Agile development schedule spanning 16 weeks across 4 major sprints.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER III: DESIGN AND DEVELOPMENT PROCESS
    # =========================================================================
    add_h1("CHAPTER III: DESIGN AND DEVELOPMENT PROCESS")

    add_h2("3.1 FUNDAMENTAL DESIGN CONCEPTS")
    add_bullet("Transforms concrete test assertion code into abstracted relational constraint structures.", "1. Abstraction: ")
    add_bullet("Decouples the system into independent micro-modules (Jira Ingestion, AST Extractor, Vector Scorer, Gating Controller).", "2. Modularity: ")
    add_bullet("Encapsulates cryptographic secrets (GitHub App PEM, Webhook HMAC keys) within secure configuration wrappers.", "3. Information Hiding: ")
    add_bullet("Enforces strong typing and schema validation using Pydantic v2 models at all boundary interfaces.", "4. Data Integrity: ")

    add_h2("3.2 DESIGN NOTATIONS & DIAGRAMS")
    add_p(
        "The system architecture is modeled using standard Data Flow Diagrams (Yourdon / DeMarco notation) and UML Use Case modeling:"
    )

    add_h3("3.2.1 Data Flow Diagrams (Calicut University Format)")
    
    # Figure 3.1
    add_image_figure("docs/diagrams/dfd/fig_3_1_dfd_level_0.png", "Figure 3.1: Context Level Data Flow Diagram (Level 0 DFD)")
    add_p(
        "Figure 3.1 represents the Context Level DFD (Level 0). Process 0.0 (Orion Governance Engine) interfaces with four external "
        "entities (Jira Cloud, GitHub CI/CD, Developer, and QA Lead / Auditor) and persists state to the central PostgreSQL database."
    )

    # Figure 3.2
    add_image_figure("docs/diagrams/dfd/fig_3_2_dfd_level_1.png", "Figure 3.2: Level 1 System Data Flow Diagram (Subsystem Decomposition)")
    add_p(
        "Figure 3.2 decomposes Process 0.0 into five specialized subsystems: 1.0 Requirements Ingestion, 2.0 AST Test Extraction, "
        "3.0 Hybrid Risk Engine, 4.0 XAI Verbalization, and 5.0 Gating & Visualization, interacting with data stores D1 through D4."
    )

    # Figure 3.3
    add_image_figure("docs/diagrams/dfd/fig_3_3_dfd_level_2_ingestion.png", "Figure 3.3: Level 2 DFD — Subsystem 1.0 (Requirements Ingestion)")
    add_p(
        "Figure 3.3 illustrates Subsystem 1.0: parsing Jira ADF payloads (1.1), extracting quantitative constraints (1.2), and generating "
        "dense 384-dimensional vector embeddings via BGE-Small (1.3) into D1: requirements."
    )

    # Figure 3.4
    add_image_figure("docs/diagrams/dfd/fig_3_4_dfd_level_2_ast.png", "Figure 3.4: Level 2 DFD — Subsystem 2.0 (AST Test Extraction)")
    add_p(
        "Figure 3.4 details Subsystem 2.0: filtering PR diffs for Python test files (2.1), traversing AST function nodes (2.2), "
        "parsing comparison operators and assertion targets (2.3), and encoding test semantics (2.4) into D2: test_cases."
    )

    # Figure 3.5
    add_image_figure("docs/diagrams/dfd/fig_3_5_dfd_level_2_hybrid.png", "Figure 3.5: Level 2 DFD — Subsystem 3.0 (Hybrid Risk Engine)")
    add_p(
        "Figure 3.5 demonstrates Subsystem 3.0: evaluating semantic cosine distance (3.1), calculating AST structural assertion overlap (3.2), "
        "computing the convex combination 0.6*S_sem + 0.4*S_struct (3.3), and applying threshold classification (3.4) into D3: trace_links."
    )

    # Figure 3.6
    add_image_figure("docs/diagrams/dfd/fig_3_6_dfd_level_2_governance.png", "Figure 3.6: Level 2 DFD — Subsystems 4.0 & 5.0 (XAI & Governance)")
    add_p(
        "Figure 3.6 shows Subsystems 4.0 and 5.0: packaging evidence diffs (4.1), generating natural language explanations via Ollama Llama 3.1 (4.2), "
        "registering GitHub Check Run gating conclusions (5.1), and synchronizing status comments to Jira Cloud (5.2)."
    )

    add_h3("3.2.2 Use Case Modeling (Role-Based Interactions)")
    add_image_figure("docs/diagrams/use_case/use_case_diagram.png", "Figure 3.7: Use Case Diagram — Orion Role-Based Architecture")
    add_p(
        "Figure 3.7 models the functional interactions for the two active roles in Orion: QA Lead / System Administrator (full policy "
        "configuration, threshold adjustment, manual overrides, simulation, and matrix inspection) and Software Developer (evidence "
        "inspection, XAI diagnostic review, and PR verification gating)."
    )

    add_h2("3.3 DESIGN PROCESS")

    add_h3("3.3.1 Database Schema Design")
    add_p(
        "Orion utilizes a normalized relational PostgreSQL schema enhanced with the pgvector extension for high-dimensional vector search:"
    )

    # Table 3.1: requirements
    add_h3("Table 3.1: requirements Table Schema")
    t1_data = [
        ["Column Name", "Data Type", "Constraints", "Description"],
        ["id", "UUID", "PRIMARY KEY", "Unique requirement identifier"],
        ["external_key", "VARCHAR(50)", "UNIQUE, NOT NULL", "Jira Issue Key (e.g., SCRUM-1)"],
        ["title", "VARCHAR(255)", "NOT NULL", "Requirement Summary / Title"],
        ["description", "TEXT", "NULLABLE", "Parsed acceptance criteria plain text"],
        ["extracted_constraints", "JSONB", "NOT NULL", "Quantitative constraint dictionary"],
        ["embedding", "VECTOR(384)", "NOT NULL", "BGE-small dense embedding vector"],
        ["created_at", "TIMESTAMP", "NOT NULL", "Record ingestion timestamp"]
    ]
    t1 = doc.add_table(rows=len(t1_data), cols=4)
    t1.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t1)
    for r_idx, row in enumerate(t1_data):
        for c_idx, val in enumerate(row):
            cell = t1.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.2
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10)
            if r_idx == 0:
                run.font.bold = True
                set_cell_background(cell, "F1F5F9")
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    # Table 3.2: test_cases
    add_h3("Table 3.2: test_cases Table Schema")
    t2_data = [
        ["Column Name", "Data Type", "Constraints", "Description"],
        ["id", "UUID", "PRIMARY KEY", "Unique test case identifier"],
        ["file_path", "VARCHAR(255)", "NOT NULL", "Repository test file path"],
        ["function_name", "VARCHAR(128)", "NOT NULL", "Name of test function"],
        ["target_requirement", "VARCHAR(50)", "NOT NULL", "Traced Jira key from @traces"],
        ["assertions", "JSONB", "NOT NULL", "Parsed AST assertion operators and values"],
        ["embedding", "VECTOR(384)", "NOT NULL", "BGE-small dense embedding vector"],
        ["updated_at", "TIMESTAMP", "NOT NULL", "Last parsed timestamp"]
    ]
    t2 = doc.add_table(rows=len(t2_data), cols=4)
    t2.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t2)
    for r_idx, row in enumerate(t2_data):
        for c_idx, val in enumerate(row):
            cell = t2.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.2
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10)
            if r_idx == 0:
                run.font.bold = True
                set_cell_background(cell, "F1F5F9")
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    # Table 3.3: traceability_matrix
    add_h3("Table 3.3: traceability_matrix Table Schema")
    t3_data = [
        ["Column Name", "Data Type", "Constraints", "Description"],
        ["id", "UUID", "PRIMARY KEY", "Unique trace link identifier"],
        ["requirement_id", "UUID", "FK -> requirements.id", "Target requirement reference"],
        ["test_case_id", "UUID", "FK -> test_cases.id", "Target test case reference"],
        ["semantic_score", "FLOAT", "NOT NULL", "Cosine similarity score (0.0 to 1.0)"],
        ["structural_score", "FLOAT", "NOT NULL", "AST assertion comparator match score"],
        ["risk_score", "FLOAT", "NOT NULL", "0.6 * semantic + 0.4 * structural"],
        ["status", "VARCHAR(20)", "NOT NULL", "COVERED, REVIEW, DRIFTED"],
        ["is_overridden", "BOOLEAN", "DEFAULT FALSE", "Administrative manual override flag"]
    ]
    t3 = doc.add_table(rows=len(t3_data), cols=4)
    t3.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(t3)
    for r_idx, row in enumerate(t3_data):
        for c_idx, val in enumerate(row):
            cell = t3.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.2
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(10)
            if r_idx == 0:
                run.font.bold = True
                set_cell_background(cell, "F1F5F9")
            set_cell_margins(cell, top=60, bottom=60, left=100, right=100)

    add_h3("3.3.2 Normalization")
    add_bullet("All attributes are atomic primitives; 384-dimensional vector embeddings are stored in native vector types.", "• First Normal Form (1NF): ")
    add_bullet("All non-key columns depend entirely on primary keys (UUID), eliminating partial functional dependencies.", "• Second Normal Form (2NF): ")
    add_bullet("Transitive dependencies are eliminated by decoupling test metadata, matrix links, and audit trails into relational foreign keys.", "• Third Normal Form (3NF): ")

    add_h2("3.4 DEVELOPMENT APPROACH (AGILE SPRINTS)")
    add_bullet("FastAPI backend scaffolding, Jira webhook listener, and PostgreSQL pgvector integration.", "• Sprint 1 (Foundation): ")
    add_bullet("Python AST parser implementation and BGE-Small ONNX vector embedding pipeline.", "• Sprint 2 (Core Parsing): ")
    add_bullet("GitHub App Check Run integration, local Ollama Llama 3.1 XAI synthesis, and dual-scoring risk engine.", "• Sprint 3 (Intelligence): ")
    add_bullet("React frontend dashboard, RBAC session gating, Ruff linting, and comprehensive automated test suite.", "• Sprint 4 (Governance): ")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER IV: CODING
    # =========================================================================
    add_h1("CHAPTER IV: CODING")

    add_h2("4.1 FRONTEND ARCHITECTURE")
    add_p(
        "The user interface is engineered with React 18 and Vite, incorporating an enterprise dark design system, CSS variables, "
        "and strict role-based presentation rules:"
    )
    add_bullet("Root application component hosting active user state, trigger handlers, and modal overlays.", "• App.jsx: ")
    add_bullet("Role-Based Access Control session gate allowing users to authenticate as QA Lead or Software Developer.", "• LoginModal.jsx: ")
    add_bullet("Traceability Matrix table featuring real-time search, status pill badges, and role-locked override buttons.", "• MatrixTable.jsx: ")
    add_bullet("Interactive dual-range sliders allowing QA Leads to reclassify matrix boundaries dynamically.", "• SensitivitySlider.jsx: ")
    add_bullet("Executive metric bar presenting real-time counts (Total, Covered, Review, Drifted) and confidence averages.", "• StatsBar.jsx: ")

    add_h2("4.2 BACKEND ARCHITECTURE")
    add_bullet("FastAPI entry point initializing CORS middleware, database connection pools, and REST routers.", "• orion/app.py: ")
    add_bullet("Asynchronous HMAC-SHA256 signature verification validating incoming GitHub pull request webhooks.", "• orion/github/webhook.py: ")
    add_bullet("GitHub App authentication exchanging RSA private key JWTs for short-lived installation access tokens.", "• orion/github/auth.py: ")
    add_bullet("Atlassian Document Format (ADF) parser extracting clean plain text with recursion depth protection.", "• orion/jira/adf.py: ")
    add_bullet("PostgreSQL connection engine providing asynchronous sessions with pgvector extension support.", "• orion/database.py: ")

    add_h2("4.3 AI & PARSER SUBSYSTEMS")
    add_bullet("Python AST visitor extracting @traces keys, function docstrings, assertion comparators, and operands.", "• orion/extraction/ast_parser.py: ")
    add_bullet("Loads BAAI/bge-small-en-v1.5 via ONNX Runtime to produce normalized 384-dimensional dense vectors.", "• orion/extraction/embedding.py: ")
    add_bullet("Dual-scoring mathematical engine computing convex combination S_hybrid = 0.6*S_sem + 0.4*S_struct.", "• orion/analysis/risk_engine.py: ")
    add_bullet("Local Ollama client invoking Meta Llama 3.1 8B with structured diff context to verbalize gap explanations.", "• orion/verbalization/service.py: ")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER V: TESTING AND IMPLEMENTATION
    # =========================================================================
    add_h1("CHAPTER V: TESTING AND IMPLEMENTATION")

    add_h2("5.1 TESTING METHODOLOGIES")
    add_p("Orion underwent thorough automated unit, integration, and validation testing across all subsystems:")

    add_h3("5.1.1 Unit Testing")
    add_bullet("Tested AST visitor across complex syntax (multi-line asserts, comparison chaining, membership tests).", "• AST Parsing: ")
    add_bullet("Validated cosine similarity and structural keyword overlap against deterministic mathematical baselines.", "• Scoring Engine: ")

    add_h3("5.1.2 Integration Testing")
    add_bullet("Validated end-to-end Jira webhook receipt, text extraction, embedding creation, and pgvector storage.", "• Ingestion Pipeline: ")
    add_bullet("Verified GitHub App JWT authentication and Check Run creation via asynchronous HTTPX clients.", "• GitHub Integration: ")

    add_h3("5.1.3 Validation Testing")
    add_bullet("Enforces numeric slider constraints (0 <= tau_struct < tau_sem <= 1.0) and RBAC role boundaries.", "• Front-End Validation: ")
    add_bullet("Pydantic models validate incoming webhook JSON structures, rejecting unauthorized payloads.", "• Back-End Validation: ")

    add_h2("5.1.4 TEST CASES AND RESULTS CHART")
    
    tc_data = [
        ["Test ID", "Component", "Test Scenario", "Expected Result", "Actual Result", "Verdict"],
        ["TC-01", "RBAC Auth", "Developer Role Lockout", "Sliders & Overrides locked", "Controls disabled with tooltip", "PASS"],
        ["TC-02", "AST Parser", "Extract @traces Decorator", "Extract target key 'SCRUM-1'", "Parsed key: 'SCRUM-1'", "PASS"],
        ["TC-03", "Risk Engine", "Covered State Evaluation", "Score >= 0.70 -> COVERED", "S_hybrid = 0.84 -> COVERED", "PASS"],
        ["TC-04", "Risk Engine", "Drifted State Detection", "Assertion mismatch -> DRIFTED", "S_hybrid = 0.38 -> DRIFTED", "PASS"],
        ["TC-05", "CI Gating", "GitHub Check Run Post", "Drifted status blocks PR", "Check Run registered as failed", "PASS"],
        ["TC-06", "XAI Engine", "Ollama LLM Fallback", "Daemon down -> Fallback template", "Deterministic template logged", "PASS"]
    ]
    tc_table = doc.add_table(rows=len(tc_data), cols=6)
    tc_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tc_table)
    for r_idx, row in enumerate(tc_data):
        for c_idx, val in enumerate(row):
            cell = tc_table.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.2
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(val)
            run.font.name = 'Times New Roman'
            run.font.size = Pt(9.5)
            if r_idx == 0:
                run.font.bold = True
                set_cell_background(cell, "F1F5F9")
            if val == "PASS":
                run.font.bold = True
                run.font.color.rgb = RGBColor(21, 128, 61)
            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)

    add_h2("5.2 QUALITY ASSURANCE & SYSTEM MAINTENANCE")
    add_p(
        "Zero blocking Ruff lint errors were permitted across the codebase. Generic risks were addressed through deterministic "
        "template fallbacks when Ollama response timeouts occur and cryptographic HMAC-SHA256 signature verification for webhooks."
    )
    add_bullet("Addressing edge-case syntax variations in newly authored unit test suites.", "• Corrective Maintenance: ")
    add_bullet("Updating Jira REST API bindings to accommodate Atlassian Cloud schema updates.", "• Adaptive Maintenance: ")
    add_bullet("Expanding AST parser support to TypeScript/Jest and Java/JUnit frameworks.", "• Perfective Maintenance: ")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER VI: CONCLUSION
    # =========================================================================
    add_h1("CHAPTER VI: CONCLUSION")

    add_h2("6.1 CONCLUSION")
    add_p(
        "The Orion platform successfully demonstrates an automated, deterministic approach to maintaining agile software compliance. "
        "By synthesizing AST code inspection with local dense vector embeddings, the system eliminates silent specification drift "
        "within active CI/CD pipelines. Empirical benchmarks confirm sub-30ms evaluation latency, while local Ollama XAI integration "
        "delivers explainable root-cause feedback without exposing intellectual property to cloud services. The implementation of "
        "role-based gating and automated GitHub Check Runs establishes a production-grade compliance platform fulfilling all "
        "objectives of the Master of Computer Applications curriculum."
    )

    add_h2("6.2 SCOPE FOR FURTHER ENHANCEMENT")
    add_bullet("Extending the AST grammar visitor to support TypeScript (Jest/Vitest) and Java (JUnit).", "1. Multi-Language AST Support: ")
    add_bullet("Replacing the in-memory token cache with Redis to support distributed multi-worker deployments.", "2. Distributed Caching: ")
    add_bullet("Leveraging local LLMs to generate automated assertion code fixes as GitHub pull request review suggestions.", "3. Automated Assertion Synthesis: ")
    add_bullet("Permitting approved test parameter adjustments to automatically update Jira acceptance criteria.", "4. Bidirectional Jira Synchronization: ")

    add_h2("6.3 BIBLIOGRAPHY")
    bib_items = [
        "Atlassian. (2024). Atlassian Document Format (ADF) Specifications. Atlassian Developer Documentation.",
        "Python Software Foundation. (2024). The AST Module: Abstract Syntax Trees. Python 3 Documentation.",
        "Xiao, S., Liu, Z., Zhang, P., & Muennighoff, N. (2023). C-Pack: Packaged Resources to Advance General Chinese Embedding. arXiv preprint arXiv:2309.07597 (BGE Models).",
        "AI @ Meta. (2024). The Llama 3 Herd of Models. Meta Research Technical Report.",
        "PostgreSQL Global Development Group. (2024). pgvector: Open-source vector similarity search for PostgreSQL.",
        "Pressman, R. S., & Maxim, B. R. (2020). Software Engineering: A Practitioner's Approach (9th ed.). McGraw-Hill Education."
    ]
    for b in bib_items:
        add_bullet(b)

    doc.add_page_break()

    # =========================================================================
    # ANNEXURES
    # =========================================================================
    add_h1("ANNEXURE - A: MAJOR INPUT AND OUTPUT SCREENS")
    
    add_h2("A.1 MAJOR INPUT SCREENS")
    add_bullet("Provides credential and role selection (QA Lead / System Administrator vs. Software Developer) with live demo presets.", "1. Authentication Session Gate (LoginModal.jsx): ")
    add_bullet("Dual-range range sliders allowing QA Leads to configure semantic and structural classification sensitivity boundaries.", "2. Sensitivity Configuration Controls (SensitivitySlider.jsx): ")
    add_bullet("Modal dialog enabling QA Leads to authoritatively override matrix link statuses with mandatory audit justifications.", "3. Manual Override Modal (MatrixTable.jsx): ")

    add_h2("A.2 MAJOR OUTPUT SCREENS")
    add_bullet("Interactive grid displaying requirement keys, linked test functions, dual scores, composite risk, and status badges.", "1. Traceability Matrix Table (MatrixTable.jsx): ")
    add_bullet("Modal window presenting natural language explanations generated by local Ollama Llama 3.1 for unverified acceptance criteria.", "2. XAI Drift Explanation Modal (HeatmapModal.jsx): ")
    add_bullet("Pull request interface in GitHub displaying pass/fail check run conclusions and line-level code annotations.", "3. GitHub Check Run Gating Summary: ")

    add_h1("ANNEXURE - B: TABLE OF ABBREVIATIONS")
    
    abbr_data = [
        ("ADF", "Atlassian Document Format"),
        ("AI", "Artificial Intelligence"),
        ("API", "Application Programming Interface"),
        ("AST", "Abstract Syntax Tree"),
        ("CI/CD", "Continuous Integration / Continuous Deployment"),
        ("DFD", "Data Flow Diagram"),
        ("FK", "Foreign Key"),
        ("HMAC", "Hash-based Message Authentication Code"),
        ("HNSW", "Hierarchical Navigable Small World"),
        ("LLM", "Large Language Model"),
        ("MCA", "Master of Computer Applications"),
        ("ONNX", "Open Neural Network Exchange"),
        ("ORM", "Object Relational Mapping"),
        ("PK", "Primary Key"),
        ("PR", "Pull Request"),
        ("RBAC", "Role-Based Access Control"),
        ("REST", "Representational State Transfer"),
        ("RTM", "Requirements Traceability Matrix"),
        ("SLA", "Service Level Agreement"),
        ("SRS", "Software Requirement Specification"),
        ("UI", "User Interface"),
        ("UUID", "Universally Unique Identifier"),
        ("VCS", "Version Control System"),
        ("XAI", "Explainable Artificial Intelligence")
    ]
    
    abbr_table = doc.add_table(rows=len(abbr_data) + 1, cols=2)
    abbr_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(abbr_table)
    
    # Header
    abbr_table.rows[0].cells[0].paragraphs[0].add_run("Abbreviation").font.bold = True
    abbr_table.rows[0].cells[1].paragraphs[0].add_run("Expanded Description").font.bold = True
    set_cell_background(abbr_table.rows[0].cells[0], "F1F5F9")
    set_cell_background(abbr_table.rows[0].cells[1], "F1F5F9")
    set_cell_margins(abbr_table.rows[0].cells[0], top=60, bottom=60, left=100, right=100)
    set_cell_margins(abbr_table.rows[0].cells[1], top=60, bottom=60, left=100, right=100)
    
    for idx, (abbr, desc) in enumerate(abbr_data):
        row = abbr_table.rows[idx + 1]
        c1, c2 = row.cells[0], row.cells[1]
        c1.width = Inches(2.0)
        c2.width = Inches(4.5)
        
        p1 = c1.paragraphs[0]
        p1.paragraph_format.line_spacing = 1.2
        p1.paragraph_format.space_after = Pt(2)
        r1 = p1.add_run(abbr)
        r1.font.name = 'Times New Roman'
        r1.font.size = Pt(11)
        r1.font.bold = True
        
        p2 = c2.paragraphs[0]
        p2.paragraph_format.line_spacing = 1.2
        p2.paragraph_format.space_after = Pt(2)
        r2 = p2.add_run(desc)
        r2.font.name = 'Times New Roman'
        r2.font.size = Pt(11)
        
        set_cell_margins(c1, top=50, bottom=50, left=100, right=100)
        set_cell_margins(c2, top=50, bottom=50, left=100, right=100)

    # Save
    doc.save(doc_path)
    print(f"Successfully generated: {doc_path} (Size: {os.path.getsize(doc_path)} bytes)")

if __name__ == "__main__":
    build_report()
