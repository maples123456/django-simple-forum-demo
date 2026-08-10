#!/usr/bin/env python3
"""Render the forum metrics Markdown guide as a layout-stable PDF."""

import html
import re
import unicodedata
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    PageBreakIfNotEmpty,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs' / 'forum-metrics-assessment-guide.md'
OUTPUT = ROOT / 'output' / 'pdf' / 'forum-metrics-assessment-guide.pdf'
FONT_REGULAR = Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
FONT_BOLD = Path('/System/Library/Fonts/STHeiti Medium.ttc')


def register_fonts():
    pdfmetrics.registerFont(TTFont('ForumCJK', str(FONT_REGULAR)))
    try:
        pdfmetrics.registerFont(TTFont('ForumCJKBold', str(FONT_BOLD), subfontIndex=0))
    except Exception:
        pdfmetrics.registerFont(TTFont('ForumCJKBold', str(FONT_REGULAR)))
    pdfmetrics.registerFontFamily(
        'ForumCJK',
        normal='ForumCJK',
        bold='ForumCJKBold',
        italic='ForumCJK',
        boldItalic='ForumCJKBold',
    )


def display_width(value):
    return sum(2 if unicodedata.east_asian_width(character) in {'W', 'F'} else 1 for character in value)


def inline_markup(value):
    placeholders = {}

    def store_code(match):
        key = f'CODETOKEN{len(placeholders)}TOKEN'
        placeholders[key] = f'<font color="#4338ca">{html.escape(match.group(1))}</font>'
        return key

    value = re.sub(r'`([^`]+)`', store_code, value)
    value = html.escape(value)
    value = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', value)
    for key, replacement in placeholders.items():
        value = value.replace(key, replacement)
    return value


def parse_table(lines, styles, available_width):
    rows = [[cell.strip() for cell in line.strip()[1:-1].split('|')] for line in lines]
    content = [rows[0], *rows[2:]]
    column_count = len(content[0])
    raw_widths = [
        max(4, min(34, max(display_width(row[column]) for row in content)))
        for column in range(column_count)
    ]
    width_sum = sum(raw_widths)
    column_widths = [available_width * width / width_sum for width in raw_widths]
    font_size = 6.4 if column_count >= 7 else 7.4 if column_count >= 5 else 8.3
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Body'],
        fontSize=font_size,
        leading=font_size + 2,
        alignment=TA_CENTER,
        wordWrap='CJK',
    )
    header_style = ParagraphStyle(
        'TableHeader',
        parent=cell_style,
        fontName='ForumCJKBold',
        textColor=colors.white,
    )
    table_data = [
        [Paragraph(inline_markup(cell), header_style) for cell in content[0]],
        *[[Paragraph(inline_markup(cell), cell_style) for cell in row] for row in content[1:]],
    ]
    table = Table(table_data, colWidths=column_widths, repeatRows=1, hAlign='CENTER')
    commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.55, colors.HexColor('#98a2b3')),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]
    for row_index in range(1, len(table_data)):
        if row_index % 2 == 0:
            commands.append(('BACKGROUND', (0, row_index), (-1, row_index), colors.HexColor('#f5f3ff')))
    table.setStyle(TableStyle(commands))
    return table


def build_styles():
    base = getSampleStyleSheet()
    return {
        'Title': ParagraphStyle(
            'Title',
            parent=base['Title'],
            fontName='ForumCJKBold',
            fontSize=24,
            leading=31,
            textColor=colors.HexColor('#182033'),
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        'H2': ParagraphStyle(
            'H2',
            parent=base['Heading2'],
            fontName='ForumCJKBold',
            fontSize=16,
            leading=21,
            textColor=colors.HexColor('#3730a3'),
            spaceBefore=8,
            spaceAfter=8,
            keepWithNext=True,
        ),
        'H3': ParagraphStyle(
            'H3',
            parent=base['Heading3'],
            fontName='ForumCJKBold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#1d2939'),
            spaceBefore=7,
            spaceAfter=5,
            keepWithNext=True,
        ),
        'H4': ParagraphStyle(
            'H4',
            parent=base['Heading4'],
            fontName='ForumCJKBold',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#475467'),
            spaceBefore=5,
            spaceAfter=3,
            keepWithNext=True,
        ),
        'Body': ParagraphStyle(
            'Body',
            parent=base['BodyText'],
            fontName='ForumCJK',
            fontSize=9,
            leading=14,
            textColor=colors.HexColor('#344054'),
            alignment=TA_LEFT,
            wordWrap='CJK',
            spaceAfter=5,
        ),
        'Bullet': ParagraphStyle(
            'Bullet',
            parent=base['BodyText'],
            fontName='ForumCJK',
            fontSize=8.8,
            leading=13,
            leftIndent=15,
            firstLineIndent=-8,
            textColor=colors.HexColor('#344054'),
            wordWrap='CJK',
            spaceAfter=2,
        ),
        'Code': ParagraphStyle(
            'Code',
            parent=base['Code'],
            fontName='ForumCJK',
            fontSize=8,
            leading=12,
            leftIndent=10,
            rightIndent=10,
            backColor=colors.HexColor('#f2f4f7'),
            borderPadding=7,
            spaceBefore=4,
            spaceAfter=7,
        ),
        'Callout': ParagraphStyle(
            'Callout',
            parent=base['BodyText'],
            fontName='ForumCJK',
            fontSize=9,
            leading=14,
            textColor=colors.HexColor('#3730a3'),
            backColor=colors.HexColor('#eeecff'),
            borderColor=colors.HexColor('#c7c2ff'),
            borderWidth=0.7,
            borderPadding=8,
            spaceBefore=4,
            spaceAfter=8,
            wordWrap='CJK',
        ),
    }


def markdown_to_story(text, styles, available_width):
    lines = text.splitlines()
    story = []
    paragraph_lines = []
    exam_count = 0

    def flush_paragraph():
        if paragraph_lines:
            story.append(Paragraph(inline_markup(' '.join(paragraph_lines)), styles['Body']))
            paragraph_lines.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            index += 1
            continue
        if stripped.startswith('|') and stripped.endswith('|'):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                table_lines.append(lines[index])
                index += 1
            story.extend([parse_table(table_lines, styles, available_width), Spacer(1, 7)])
            continue
        if stripped.startswith('```'):
            flush_paragraph()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].strip().startswith('```'):
                code_lines.append(lines[index])
                index += 1
            story.append(Preformatted('\n'.join(code_lines), styles['Code']))
            index += 1
            continue
        if stripped == '---':
            flush_paragraph()
            next_index = index + 1
            while next_index < len(lines) and not lines[next_index].strip():
                next_index += 1
            if next_index < len(lines) and re.match(r'^##\s+考核', lines[next_index].strip()):
                index += 1
                continue
            story.extend([Spacer(1, 5), HRFlowable(width='100%', thickness=0.7, color=colors.HexColor('#d0d5dd')), Spacer(1, 5)])
            index += 1
            continue
        heading = re.match(r'^(#{1,4})\s+(.+)$', stripped)
        if heading:
            flush_paragraph()
            level = len(heading.group(1))
            title = heading.group(2)
            if level == 2 and title.startswith('考核'):
                if exam_count:
                    story.append(PageBreak())
                exam_count += 1
            style = styles['Title'] if level == 1 else styles[f'H{level}']
            if title == '对应参考答案':
                # A long question may already have flowed onto a fresh page.
                # Avoid emitting a second break and creating a blank PDF page.
                story.append(PageBreakIfNotEmpty())
                style = ParagraphStyle('AnswerHeading', parent=styles['H3'], textColor=colors.HexColor('#067647'))
            if title in {'一票否决错误', '全局一票否决错误'}:
                style = ParagraphStyle('ErrorHeading', parent=styles['H3'], textColor=colors.HexColor('#b42318'))
            story.append(Paragraph(inline_markup(title), style))
            index += 1
            continue
        if stripped.startswith('> '):
            flush_paragraph()
            story.append(Paragraph(inline_markup(stripped[2:]), styles['Callout']))
            index += 1
            continue
        bullet = re.match(r'^[-*]\s+(.+)$', stripped)
        numbered = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        if bullet or numbered:
            flush_paragraph()
            label = '•' if bullet else f'{numbered.group(1)}.'
            value = bullet.group(1) if bullet else numbered.group(2)
            story.append(Paragraph(inline_markup(value), styles['Bullet'], bulletText=label))
            index += 1
            continue
        paragraph_lines.append(stripped)
        index += 1
    flush_paragraph()
    return story


def decorate_page(canvas, document):
    canvas.saveState()
    width, height = landscape(A4)
    canvas.setStrokeColor(colors.HexColor('#d0d5dd'))
    canvas.setLineWidth(0.4)
    canvas.line(18 * mm, 13 * mm, width - 18 * mm, 13 * mm)
    canvas.setFont('ForumCJK', 7.5)
    canvas.setFillColor(colors.HexColor('#667085'))
    canvas.drawString(18 * mm, 8 * mm, '论坛常见指标能力评估手册')
    canvas.drawRightString(width - 18 * mm, 8 * mm, f'第 {document.page} 页')
    canvas.restoreState()


def main():
    register_fonts()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    page_width, _ = landscape(A4)
    margin = 18 * mm
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=landscape(A4),
        leftMargin=margin,
        rightMargin=margin,
        topMargin=12 * mm,
        bottomMargin=17 * mm,
        title='论坛常见指标能力评估手册',
        author='django-simple-forum-demo',
    )
    styles = build_styles()
    story = markdown_to_story(SOURCE.read_text(), styles, page_width - 2 * margin)
    document.build(story, onFirstPage=decorate_page, onLaterPages=decorate_page)
    print(OUTPUT)


if __name__ == '__main__':
    main()
