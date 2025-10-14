# app.py
import os
import threading
import queue
import uuid
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from parser import parse_resume
from matcher import tfidf_similarity, semantic_similarity_by_embeddings, llm_score_resume
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, static_folder='../frontend/dist', static_url_path='/')
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'app.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + DB_PATH
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Background job queue
job_queue = queue.Queue()
WORKER_SHUTDOWN = threading.Event()

# Load skills master
SKILLS_FILE = os.path.join(BASE_DIR, 'skills.txt')
with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
    SKILLS_MASTER = [line.strip() for line in f if line.strip()]

class Resume(db.Model):
    id = db.Column(db.String, primary_key=True)
    filename = db.Column(db.String)
    text = db.Column(db.Text)
    parsed = db.Column(db.Text)  # JSON blob of parsed fields
    created_at = db.Column(db.Float, default=time.time)

class JobDescription(db.Model):
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    description = db.Column(db.Text)
    created_at = db.Column(db.Float, default=time.time)

class MatchResult(db.Model):
    id = db.Column(db.String, primary_key=True)
    resume_id = db.Column(db.String, db.ForeignKey('resume.id'))
    job_id = db.Column(db.String, db.ForeignKey('job_description.id'))
    status = db.Column(db.String, default='queued')  # queued, running, done, failed
    tfidf = db.Column(db.Float)
    embedding = db.Column(db.Float)
    llm_result = db.Column(db.Text)
    created_at = db.Column(db.Float, default=time.time)
    updated_at = db.Column(db.Float, default=time.time, onupdate=time.time)

db.create_all()

def worker_loop():
    while not WORKER_SHUTDOWN.is_set():
        try:
            job = job_queue.get(timeout=1)
        except queue.Empty:
            continue
        match_id = job['match_id']
        try:
            process_match_job(match_id)
        except Exception as e:
            mr = MatchResult.query.get(match_id)
            if mr:
                mr.status = 'failed'
                mr.llm_result = str(e)
                db.session.commit()
        finally:
            job_queue.task_done()

def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    return t

def enqueue_match(resume_id, job_id):
    match_id = str(uuid.uuid4())
    mr = MatchResult(id=match_id, resume_id=resume_id, job_id=job_id, status='queued')
    db.session.add(mr)
    db.session.commit()
    job_queue.put({'match_id': match_id})
    return match_id

def process_match_job(match_id):
    mr = MatchResult.query.get(match_id)
    if not mr:
        return
    mr.status = 'running'
    db.session.commit()
    resume = Resume.query.get(mr.resume_id)
    job = JobDescription.query.get(mr.job_id)
    if not resume or not job:
        mr.status = 'failed'
        db.session.commit()
        return
    # ensure parsed
    parsed = {}
    if not resume.parsed:
        parsed = {'text': resume.text, 'skills': []}
        resume.parsed = json.dumps(parsed)
        db.session.commit()
    else:
        parsed = json.loads(resume.parsed)
    resume_text = resume.text or ''
    job_desc = job.description or ''
    try:
        tfidf = tfidf_similarity(resume_text, job_desc)
    except Exception:
        tfidf = None
    try:
        emb = semantic_similarity_by_embeddings(resume_text, job_desc)
    except Exception:
        emb = None
    try:
        llm = llm_score_resume(resume_text, job_desc, parsed.get('skills', []))
    except Exception as e:
        llm = f"LLM error: {e}"
    mr.tfidf = tfidf
    mr.embedding = emb
    mr.llm_result = llm
    mr.status = 'done'
    db.session.commit()

import json
def json_dumps(x): return json.dumps(x)
def json_loads(x): return json.loads(x) if x else {}

@app.route('/api/upload', methods=['POST'])
def upload_resume():
    if 'resume' not in request.files:
        return jsonify({'error':'provide resume file under "resume"'}), 400
    f = request.files['resume']
    uid = str(uuid.uuid4())
    save_dir = os.path.join(BASE_DIR, 'uploads')
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, uid + '_' + f.filename)
    f.save(path)
    # try parse to extract text
    try:
        parsed = parse_resume(path, SKILLS_MASTER)
        text = parsed.get('text', '')
    except Exception:
        with open(path, 'rb') as ff:
            text = ff.read().decode(errors='ignore')
        parsed = {'text': text}
    r = Resume(id=uid, filename=path, text=text, parsed=json.dumps(parsed))
    db.session.add(r)
    db.session.commit()
    return jsonify({'resume_id': uid, 'parsed_preview': parsed}), 201

@app.route('/api/resumes', methods=['GET'])
def list_resumes():
    res = []
    for r in Resume.query.order_by(Resume.created_at.desc()).all():
        res.append({'id': r.id, 'filename': os.path.basename(r.filename), 'created_at': r.created_at})
    return jsonify(res)

@app.route('/api/jobs', methods=['POST'])
def create_job():
    data = request.get_json()
    title = data.get('title') or 'Untitled'
    desc = data.get('description') or ''
    jid = str(uuid.uuid4())
    job = JobDescription(id=jid, title=title, description=desc)
    db.session.add(job)
    db.session.commit()
    return jsonify({'job_id': jid})

@app.route('/api/match', methods=['POST'])
def create_match():
    data = request.get_json()
    resume_id = data.get('resume_id')
    job_id = data.get('job_id')
    if not resume_id or not job_id:
        return jsonify({'error':'resume_id and job_id required'}), 400
    match_id = enqueue_match(resume_id, job_id)
    return jsonify({'match_id': match_id}), 202

@app.route('/api/matches', methods=['GET'])
def list_matches():
    res = []
    for m in MatchResult.query.order_by(MatchResult.created_at.desc()).all():
        res.append({
            'id': m.id,
            'resume_id': m.resume_id,
            'job_id': m.job_id,
            'status': m.status,
            'tfidf': m.tfidf,
            'embedding': m.embedding,
            'llm_result': m.llm_result
        })
    return jsonify(res)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    dist = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist')
    if path != '' and os.path.exists(os.path.join(dist, path)):
        return send_from_directory(dist, path)
    index = os.path.join(dist, 'index.html')
    if os.path.exists(index):
        return send_from_directory(dist, 'index.html')
    return jsonify({'msg':'Frontend not built; run frontend dev server.'})

if __name__ == '__main__':
    worker = start_worker()
    try:
        app.run(debug=True, port=5000)
    finally:
        WORKER_SHUTDOWN.set()
