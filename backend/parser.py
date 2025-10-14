# parser.py
import re
from pdfminer.high_level import extract_text
from collections import defaultdict

def extract_text_from_pdf(path):
    try:
        return extract_text(path)
    except Exception:
        with open(path, 'rb') as f:
            return f.read().decode(errors='ignore')

def simple_extract_sections(text):
    sections = defaultdict(str)
    headings = ['experience', 'work experience', 'professional experience', 'education', 'skills', 'technical skills', 'projects']
    lines = text.splitlines()
    cur = 'text'
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        l = line_stripped.lower()
        found = False
        for h in headings:
            if l.startswith(h):
                cur = h
                found = True
                break
        if not found:
            sections[cur] += line_stripped + '\n'
    return {
        'experience': sections.get('experience', ''),
        'education': sections.get('education', ''),
        'skills_section': sections.get('skills', '') or sections.get('technical skills', ''),
        'text': text
    }

def extract_education(text):
    edu = []
    year_pattern = re.compile(r'(?:(?:19|20)\d{2})')
    lines = text.splitlines()
    for line in lines:
        if any(k in line.lower() for k in ['bachelor', 'b.tech', 'bsc', 'msc', 'master', 'phd', 'graduate', 'degree', 'diploma', 'mba']):
            years = year_pattern.findall(line)
            edu.append({'line': line.strip(), 'years': years})
    return edu

def extract_experience_years(text):
    patterns = [
        r'(\b(?:19|20)\d{2})\s*[-–]\s*(?:present|now|current)|(\b(?:19|20)\d{2})\s*[-–]\s*(\b(?:19|20)\d{2})',
        r'(\d+)\s+years'
    ]
    years = []
    for p in patterns:
        for m in re.finditer(p, text, flags=re.IGNORECASE):
            years.extend([g for g in m.groups() if g])
    numeric_years = []
    for y in years:
        try:
            numeric_years.append(int(y))
        except:
            pass
    total_exp = None
    if len(numeric_years) >= 2:
        total_exp = abs(numeric_years[-1] - numeric_years[0])
    else:
        m = re.search(r'(\d+)\s+years', text, flags=re.IGNORECASE)
        if m:
            total_exp = int(m.group(1))
    return total_exp

def extract_skills_from_section(skills_section, skills_master_list):
    found = set()
    text = skills_section.lower()
    for skill in skills_master_list:
        if skill.lower() in text:
            found.add(skill)
    return list(found)

def parse_resume(path, skills_master_list):
    text = extract_text_from_pdf(path)
    secs = simple_extract_sections(text)
    education = extract_education(secs['education'] or secs['text'])
    experience_years = extract_experience_years(secs['experience'] or secs['text'])
    skills = extract_skills_from_section(secs['skills_section'] or secs['text'], skills_master_list)
    return {
        'text': text,
        'education': education,
        'experience_years': experience_years,
        'skills': skills
    }
