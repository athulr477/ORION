import os
import re
import glob
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

def configure_document(doc):
    # Set paper size to A4
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    
    # Set Margins
    section.left_margin = Inches(1.5)
    section.right_margin = Inches(1.0)
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)

    # Configure styles
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    style_normal.paragraph_format.line_spacing = 1.5
    style_normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    # Chapter Title Style
    style_chapter = doc.styles.add_style('ChapterTitle', WD_STYLE_TYPE.PARAGRAPH)
    style_chapter.base_style = doc.styles['Heading 1']
    font_chapter = style_chapter.font
    font_chapter.name = 'Times New Roman'
    font_chapter.size = Pt(16)
    font_chapter.bold = True
    font_chapter.color.rgb = RGBColor(0, 0, 0)
    style_chapter.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    style_chapter.paragraph_format.space_after = Pt(24)

    # Heading 1 Style (for sections like 1.1)
    style_h1 = doc.styles.add_style('SectionHeading', WD_STYLE_TYPE.PARAGRAPH)
    style_h1.base_style = doc.styles['Heading 2']
    font_h1 = style_h1.font
    font_h1.name = 'Times New Roman'
    font_h1.size = Pt(14)
    font_h1.bold = True
    font_h1.color.rgb = RGBColor(0, 0, 0)
    style_h1.paragraph_format.space_before = Pt(18)
    style_h1.paragraph_format.space_after = Pt(12)

    # Heading 2 Style (for subsections like 1.1.1)
    style_h2 = doc.styles.add_style('SubSectionHeading', WD_STYLE_TYPE.PARAGRAPH)
    style_h2.base_style = doc.styles['Heading 3']
    font_h2 = style_h2.font
    font_h2.name = 'Times New Roman'
    font_h2.size = Pt(12)
    font_h2.bold = True
    font_h2.color.rgb = RGBColor(0, 0, 0)
    style_h2.paragraph_format.space_before = Pt(12)
    style_h2.paragraph_format.space_after = Pt(6)
    
def find_image(figure_text, image_dir):
    # Parse e.g. "FIGURE 3.1" -> "3_1"
    match = re.search(r'FIGURE\s+(\d+)\.(\d+)', figure_text)
    if match:
        major, minor = match.groups()
        pattern = f"*fig_{major}_{minor}_*.png"
        matches = glob.glob(os.path.join(image_dir, pattern))
        if matches:
            return matches[0]
    return None

def main():
    doc = Document()
    configure_document(doc)

    # Resolve project root dynamically from this file's location:
    # backend/scripts/build_full_mca_report.py → parents[2] = ORION/
    _project_root = Path(__file__).resolve().parents[2]

    input_file = _project_root / "full_report_structure.md"
    output_dir = _project_root / "docs" / "report"
    os.makedirs(output_dir, exist_ok=True)
    output_file = output_dir / "Orion_MCA_Final_Project_Report_Complete.docx"

    image_dir = _project_root / "docs" / "diagrams" / "dfd"

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_table = False
    table_data = []
    
    # helper for processing table
    def process_table(data):
        if not data: return
        num_cols = len(data[0])
        table = doc.add_table(rows=1, cols=num_cols)
        table.style = 'Table Grid'
        
        # Header
        hdr_cells = table.rows[0].cells
        for i, col_name in enumerate(data[0]):
            hdr_cells[i].text = col_name.strip()
            # bold header
            for paragraph in hdr_cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
                    run.font.name = 'Times New Roman'
                    
        # Rows
        for row_data in data[1:]:
            row_cells = table.add_row().cells
            # if separator row, skip
            if set(row_data[0].strip()) == {'-', ':'}:
                continue
            for i, cell_val in enumerate(row_data):
                if i < len(row_cells):
                    row_cells[i].text = cell_val.strip()
                    for paragraph in row_cells[i].paragraphs:
                        for run in paragraph.runs:
                            run.font.name = 'Times New Roman'
                            
    for idx, line in enumerate(lines):
        line = line.strip()
        
        if line.startswith('=' * 20):
            # Page break
            if len(doc.paragraphs) > 0:
                doc.add_page_break()
            continue
            
        if line.startswith('CHAPTER') or (line.startswith('#') and 'PROJECT REPORT' in lines[max(0, idx-1):idx+2]):
             if 'CHAPTER' in line:
                 doc.add_paragraph(line, style='ChapterTitle')
             elif line.startswith('#'):
                 doc.add_paragraph(line.replace('#', '').strip(), style='ChapterTitle')
             continue
             
        # Section Headings (e.g., "1.1 ", "2.1 ")
        if re.match(r'^\d+\.\d+\s+[A-Z]', line):
            doc.add_paragraph(line, style='SectionHeading')
            continue
            
        # Sub-section Headings (e.g., "1.1.1 ")
        if re.match(r'^\d+\.\d+\.\d+\s+[A-Z]', line):
            doc.add_paragraph(line, style='SubSectionHeading')
            continue

        # Annexure headings
        if line.startswith('ANNEXURE'):
            if len(doc.paragraphs) > 0:
                doc.add_page_break()
            doc.add_paragraph(line, style='ChapterTitle')
            continue

        # Tables (e.g. "Table 3.1: ...")
        if re.match(r'^Table\s+\d+\.\d+:', line) or in_table:
            if not in_table:
                # Add table title
                doc.add_paragraph(line, style='Normal').runs[0].bold = True
                continue
        
        # Check for table rows (contains pipe |)
        if '|' in line:
            in_table = True
            row_cols = [x.strip() for x in line.split('|') if x.strip()]
            if line.strip().startswith('|'):
                # properly split for markdown tables
                pass
            table_data.append(row_cols)
            continue
        elif in_table and line.strip() == '':
            in_table = False
            process_table(table_data)
            table_data = []
            continue
            
        # Figures
        if line.startswith('[INSERT FIGURE'):
            img_path = find_image(line, image_dir)
            if img_path:
                doc.add_picture(img_path, width=Inches(5.5))
                # Add caption
                caption_text = line.replace('[INSERT ', '').replace(']', '')
                p = doc.add_paragraph(caption_text)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.runs[0].italic = True
            else:
                # If image not found, just add placeholder text
                doc.add_paragraph(line)
            continue

        if not in_table and line:
            p = doc.add_paragraph(line, style='Normal')
            # Check for bold text e.g. **bold**
            if '**' in line:
                pass # Simple handling, relying on pure text is mostly fine. We can just insert it.

    if in_table:
        process_table(table_data)
        
    doc.save(output_file)
    print(f"Generated {output_file}")

if __name__ == '__main__':
    main()
