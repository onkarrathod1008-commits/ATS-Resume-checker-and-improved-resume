from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs
import json
import re


PORT = 8081

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "for", "from",
    "has", "have", "in", "is", "it", "its", "of", "on", "or", "our", "that",
    "the", "their", "this", "to", "with", "will", "you", "your", "we", "work",
    "role", "job", "team", "candidate", "experience", "skills",
    "responsibilities", "requirements", "required", "hiring", "hire"
}

ACTION_VERBS = {
    "built", "created", "developed", "designed", "implemented", "improved",
    "optimized", "automated", "delivered", "managed", "led", "launched",
    "reduced", "increased", "integrated", "tested", "deployed", "analyzed",
    "migrated", "maintained"
}


def clean_text(value):
    return (value or "").lower()


def contains_digit(value):
    return any(ch.isdigit() for ch in value)


def top_keywords(text, limit=28):
    words = re.findall(r"[a-z0-9+#.]+", text.lower())
    counts = {}

    for raw in words:
        word = raw.strip(".,:;!?()[]{}\"'")
        if len(word) < 3 or word in STOP_WORDS:
            continue
        counts[word] = counts.get(word, 0) + 1

    sorted_words = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in sorted_words[:limit]]


def score_sections(resume_text):
    score = 0
    if "summary" in resume_text or "profile" in resume_text:
        score += 3
    if "skill" in resume_text:
        score += 4
    if "experience" in resume_text or "employment" in resume_text:
        score += 4
    if "project" in resume_text:
        score += 3
    if "education" in resume_text:
        score += 2
    return min(score, 15)


def score_achievements(resume):
    resume_text = clean_text(resume)
    score = sum(1 for verb in ACTION_VERBS if verb in resume_text)
    if contains_digit(resume):
        score += 5
    if "%" in resume:
        score += 3
    return min(score, 15)


def score_formatting(resume):
    score = 10
    if len(resume) < 400:
        score -= 3
    if "|" in resume or "□" in resume or "●" in resume:
        score -= 2
    if "curriculum vitae" in resume.lower():
        score -= 1
    return max(0, min(score, 10))


def unique_join(items, limit):
    seen = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return ", ".join(seen[:limit])


def build_changes(missing_keywords, resume_text):
    changes = []
    if missing_keywords:
        changes.append("Add missing job keywords naturally: " + unique_join(missing_keywords, 8))
    if "summary" not in resume_text and "profile" not in resume_text:
        changes.append("Add a 3-line professional summary targeted to the exact job title.")
    if "project" not in resume_text and "experience" not in resume_text:
        changes.append("Add a Projects or Experience section with role-specific proof.")
    if not contains_digit(resume_text):
        changes.append("Add measurable results such as percentages, time saved, users, revenue, or performance gains.")
    if "certification" not in resume_text and "certificate" not in resume_text:
        changes.append("Add relevant certifications or coursework if you have them.")
    changes.append("Rewrite bullets using action verbs, tools used, and business/result impact.")
    return changes


def build_remove_suggestions(resume_text):
    remove = []
    if "objective" in resume_text:
        remove.append("Replace old-style Objective section with a targeted Professional Summary.")
    if "references available" in resume_text:
        remove.append("Remove 'References available on request'; it wastes resume space.")
    if any(term in resume_text for term in ["photo", "date of birth", "marital"]):
        remove.append("Remove personal details like photo, date of birth, or marital status for ATS-friendly hiring.")
    remove.append("Remove skills that are unrelated to the selected job if they push important keywords lower.")
    remove.append("Avoid tables, text boxes, icons, and heavy graphics because many ATS parsers read them poorly.")
    return remove


def build_summary(score):
    if score >= 85:
        return "Strong ATS fit. The resume already matches many role signals; polish measurable impact and keep keywords natural."
    if score >= 70:
        return "Good base. Add the missing role keywords and sharpen achievements to increase recruiter confidence."
    if score >= 50:
        return "Moderate fit. The resume needs clearer alignment with the vacancy, especially in skills and experience bullets."
    return "Low ATS fit. Rebuild the summary, skills, and project/experience bullets around the job description."


def build_improved_resume(resume, job_keywords, missing_keywords):
    focus = []
    for item in job_keywords + missing_keywords:
        if item not in focus:
            focus.append(item)

    skill_line = unique_join(focus, 14) or "Add role-specific tools, technologies, and methods from the job description."
    original = resume.strip()
    if len(original) > 1200:
        original = original[:1200] + "..."

    draft = f"""PROFESSIONAL SUMMARY
Results-focused candidate aligned with this role, with experience across {skill_line}. Strong ability to learn quickly, deliver reliable work, and communicate progress clearly.

CORE SKILLS
{skill_line}

EXPERIENCE / PROJECTS
- Developed and delivered work aligned with business requirements using relevant tools from the job description.
- Improved process quality by applying structured analysis, testing, documentation, and stakeholder feedback.
- Collaborated with team members to complete tasks on time while maintaining clean, understandable work.
- Add 2-4 bullets from your real resume here, rewritten with numbers and job-specific keywords.

EDUCATION
Keep your existing education details here.

CERTIFICATIONS
Add only certifications relevant to this job profile.

NOTES FOR YOU
This is a generated draft structure. Keep every claim truthful and replace generic bullets with your real achievements."""

    if original:
        draft += "\n\nORIGINAL RESUME CONTENT TO ADAPT\n" + original
    return draft


def analyze_resume(resume, job):
    resume_text = clean_text(resume)
    job_text = clean_text(job)

    job_keywords = top_keywords(job_text, 28)
    resume_keywords = set(top_keywords(resume_text, 45))

    matched = []
    missing = []
    for keyword in job_keywords:
        if keyword in resume_keywords or keyword in resume_text:
            matched.append(keyword)
        else:
            missing.append(keyword)

    keyword_score = round((len(matched) * 40) / len(job_keywords)) if job_keywords else 0
    section_score = score_sections(resume_text)
    achievement_score = score_achievements(resume)
    format_score = score_formatting(resume)
    relevance_score = min(20, round(keyword_score * 0.35 + achievement_score * 0.45 + section_score * 0.20))
    total = max(0, min(100, keyword_score + section_score + achievement_score + format_score + relevance_score))

    return {
        "score": total,
        "keywordScore": keyword_score,
        "sectionScore": section_score,
        "achievementScore": achievement_score,
        "formatScore": format_score,
        "relevanceScore": relevance_score,
        "summary": build_summary(total),
        "matchedKeywords": matched,
        "missingKeywords": missing,
        "changes": build_changes(missing, resume_text),
        "remove": build_remove_suggestions(resume_text),
        "improvedResume": build_improved_resume(resume, job_keywords, missing),
    }


HTML_PAGE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ATS Resume Checker</title>
  <style>
    :root { --ink:#18202a; --muted:#5c6675; --line:#d9dee7; --panel:#ffffff; --soft:#f5f7fb; --brand:#146c5c; --brand2:#0d4d88; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:#eef2f7; }
    header { background:#ffffff; border-bottom:1px solid var(--line); }
    .topbar { max-width:1180px; margin:0 auto; padding:18px 22px; display:flex; justify-content:space-between; align-items:center; gap:16px; }
    .brand { display:flex; align-items:center; gap:12px; font-weight:800; font-size:20px; }
    .mark { width:38px; height:38px; display:grid; place-items:center; border-radius:8px; background:var(--brand); color:white; font-weight:900; }
    .status { font-size:13px; color:var(--muted); border:1px solid var(--line); padding:8px 10px; border-radius:8px; background:var(--soft); }
    main { max-width:1180px; margin:0 auto; padding:24px 22px 42px; }
    .intro { display:grid; grid-template-columns:1.2fr .8fr; gap:22px; align-items:stretch; margin-bottom:22px; }
    .headline { padding:28px; background:#ffffff; border:1px solid var(--line); border-radius:8px; }
    h1 { margin:0 0 12px; font-size:34px; line-height:1.12; letter-spacing:0; }
    p { line-height:1.55; color:var(--muted); }
    .metric-row { display:grid; grid-template-columns:repeat(3, 1fr); gap:10px; margin-top:18px; }
    .mini { border:1px solid var(--line); border-radius:8px; padding:12px; background:var(--soft); min-height:72px; }
    .mini strong { display:block; font-size:20px; color:var(--ink); margin-bottom:4px; }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; }
    .side-note { padding:22px; display:flex; flex-direction:column; justify-content:center; }
    .side-note h2, .panel h2 { margin:0 0 8px; font-size:19px; }
    .grid { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
    label { display:block; font-weight:700; margin-bottom:8px; }
    textarea { width:100%; min-height:270px; resize:vertical; border:1px solid var(--line); border-radius:8px; padding:14px; font:14px/1.45 Consolas, 'Courier New', monospace; color:var(--ink); background:#fbfcfe; }
    textarea:focus { outline:3px solid rgba(20,108,92,.16); border-color:var(--brand); }
    .input-card { padding:18px; }
    .actions { display:flex; gap:10px; align-items:center; margin:18px 0 22px; flex-wrap:wrap; }
    button { border:0; border-radius:8px; padding:12px 16px; font-weight:800; cursor:pointer; font-size:14px; min-height:44px; }
    .primary { background:var(--brand); color:#fff; }
    .secondary { background:#ffffff; color:var(--ink); border:1px solid var(--line); }
    .results { display:none; grid-template-columns:330px 1fr; gap:18px; align-items:start; }
    .score-panel { padding:20px; position:sticky; top:14px; }
    .score-circle { width:190px; height:190px; border-radius:50%; margin:6px auto 18px; display:grid; place-items:center; background:conic-gradient(var(--brand) 0deg, #e6ebf2 0deg); }
    .score-inner { width:142px; height:142px; border-radius:50%; background:#fff; display:grid; place-items:center; border:1px solid var(--line); }
    .score-number { font-size:42px; font-weight:900; }
    .breakdown { display:grid; gap:9px; }
    .bar { display:grid; gap:5px; }
    .bar-top { display:flex; justify-content:space-between; font-size:13px; color:var(--muted); }
    .track { height:8px; background:#e8edf5; border-radius:99px; overflow:hidden; }
    .fill { height:100%; width:0%; background:var(--brand2); }
    .detail-stack { display:grid; gap:18px; }
    .detail { padding:18px; }
    .chips { display:flex; gap:8px; flex-wrap:wrap; margin-top:12px; }
    .chip { font-size:13px; padding:7px 9px; border-radius:999px; background:#edf6f2; color:#07543b; border:1px solid #c9e4d8; }
    .chip.missing { background:#fff4e8; color:#7a3b00; border-color:#f1d2ac; }
    ul { margin:12px 0 0; padding-left:22px; color:var(--muted); line-height:1.55; }
    .resume-output { white-space:pre-wrap; background:#f8fafc; border:1px solid var(--line); border-radius:8px; padding:14px; min-height:240px; font:14px/1.5 Consolas, 'Courier New', monospace; color:#243040; }
    .footer-note { margin-top:18px; font-size:13px; color:var(--muted); }
    @media (max-width:900px) { .intro, .grid, .results { grid-template-columns:1fr; } .score-panel { position:static; } h1 { font-size:28px; } .metric-row { grid-template-columns:1fr; } }
  </style>
</head>
<body>
  <header><div class="topbar"><div class="brand"><div class="mark">ATS</div><span>Resume Match Studio</span></div><div class="status">Python backend running locally</div></div></header>
  <main>
    <section class="intro">
      <div class="headline">
        <h1>Check your resume against a real job profile.</h1>
        <p>Paste your resume and the vacancy text. The Python analyzer scores keyword fit, section strength, measurable achievements, formatting readability, and role relevance, then drafts a cleaner ATS-friendly version.</p>
        <div class="metric-row"><div class="mini"><strong>100</strong><span>ATS-style score</span></div><div class="mini"><strong>5</strong><span>score categories</span></div><div class="mini"><strong>1</strong><span>improved draft</span></div></div>
      </div>
      <div class="panel side-note"><h2>What it helps with</h2><p>Use it before applying to compare your resume with the exact role, spot missing terms, remove weak content, and rewrite bullets with stronger evidence.</p></div>
    </section>
    <section class="grid">
      <div class="panel input-card"><label for="resume">Resume text</label><textarea id="resume" placeholder="Paste your resume content here..."></textarea></div>
      <div class="panel input-card"><label for="job">Job profile / vacancy</label><textarea id="job" placeholder="Paste job description, responsibilities, required skills, and qualifications here..."></textarea></div>
    </section>
    <div class="actions"><button class="primary" id="analyzeBtn">Analyze Resume</button><button class="secondary" id="sampleBtn">Load Sample</button><button class="secondary" id="clearBtn">Clear</button></div>
    <section class="results" id="results">
      <aside class="panel score-panel">
        <div class="score-circle" id="scoreCircle"><div class="score-inner"><div><div class="score-number" id="scoreNumber">0</div><div style="text-align:center;color:var(--muted);font-size:13px;">out of 100</div></div></div></div>
        <p id="summary"></p>
        <div class="breakdown" id="breakdown"></div>
      </aside>
      <div class="detail-stack">
        <div class="panel detail"><h2>Matched Keywords</h2><div class="chips" id="matched"></div></div>
        <div class="panel detail"><h2>Missing Keywords</h2><div class="chips" id="missing"></div></div>
        <div class="panel detail"><h2>Changes To Make</h2><ul id="changes"></ul></div>
        <div class="panel detail"><h2>Things To Remove Or Avoid</h2><ul id="remove"></ul></div>
        <div class="panel detail"><h2>Improved Resume Draft</h2><div class="resume-output" id="improved"></div></div>
      </div>
    </section>
    <p class="footer-note">Note: this estimates ATS alignment. It cannot guarantee selection because recruiters, company filters, timing, and competition also matter.</p>
  </main>
  <script>
    var resumeBox = document.getElementById('resume');
    var jobBox = document.getElementById('job');
    document.getElementById('analyzeBtn').onclick = function () {
      if (!resumeBox.value.trim() || !jobBox.value.trim()) { alert('Please paste both resume and job profile text.'); return; }
      var body = 'resume=' + encodeURIComponent(resumeBox.value) + '&job=' + encodeURIComponent(jobBox.value);
      fetch('/analyze', { method:'POST', headers:{ 'Content-Type':'application/x-www-form-urlencoded' }, body:body })
        .then(function (r) { return r.json(); })
        .then(renderResults)
        .catch(function () { alert('Could not analyze. Please check that the Python server is running.'); });
    };
    document.getElementById('sampleBtn').onclick = function () {
      resumeBox.value = 'Rahul Sharma\nEmail: rahul@example.com\n\nSkills: Java, HTML, CSS, SQL\n\nProjects\n- Created a student management system using Java and MySQL.\n- Built pages using HTML and CSS.\n\nEducation\nB.Tech Computer Science';
      jobBox.value = 'We are hiring a Java Web Developer with experience in Java, Servlets, REST API, SQL, HTML, CSS, JavaScript, Git, debugging, database design, and deployment. Candidate should build secure web applications, improve performance, and collaborate with teams.';
    };
    document.getElementById('clearBtn').onclick = function () { resumeBox.value=''; jobBox.value=''; document.getElementById('results').style.display='none'; };
    function renderResults(data) {
      document.getElementById('results').style.display = 'grid';
      document.getElementById('scoreNumber').textContent = data.score;
      document.getElementById('scoreCircle').style.background = 'conic-gradient(var(--brand) ' + (data.score * 3.6) + 'deg, #e6ebf2 0deg)';
      document.getElementById('summary').textContent = data.summary;
      renderBars(data);
      renderChips('matched', data.matchedKeywords, false);
      renderChips('missing', data.missingKeywords, true);
      renderList('changes', data.changes);
      renderList('remove', data.remove);
      document.getElementById('improved').textContent = data.improvedResume;
      document.getElementById('results').scrollIntoView({ behavior:'smooth', block:'start' });
    }
    function renderBars(data) {
      var rows = [['Keyword match', data.keywordScore, 40], ['Resume sections', data.sectionScore, 15], ['Achievements', data.achievementScore, 15], ['ATS format', data.formatScore, 10], ['Role relevance', data.relevanceScore, 20]];
      document.getElementById('breakdown').innerHTML = rows.map(function (row) {
        var pct = Math.round((row[1] / row[2]) * 100);
        return '<div class="bar"><div class="bar-top"><span>' + row[0] + '</span><strong>' + row[1] + '/' + row[2] + '</strong></div><div class="track"><div class="fill" style="width:' + pct + '%"></div></div></div>';
      }).join('');
    }
    function renderChips(id, items, missing) {
      var box = document.getElementById(id);
      if (!items.length) { box.innerHTML = '<span class="chip ' + (missing ? 'missing' : '') + '">None found</span>'; return; }
      box.innerHTML = items.slice(0, 18).map(function (item) { return '<span class="chip ' + (missing ? 'missing' : '') + '">' + escapeHtml(item) + '</span>'; }).join('');
    }
    function renderList(id, items) { document.getElementById(id).innerHTML = items.map(function (item) { return '<li>' + escapeHtml(item) + '</li>'; }).join(''); }
    function escapeHtml(value) { return String(value).replace(/[&<>"]/g, function (c) { return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  </script>
</body>
</html>"""


class ResumeCheckerHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404, "Page not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        if self.path != "/analyze":
            self.send_error(404, "Endpoint not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw_body)
        resume = form.get("resume", [""])[0]
        job = form.get("job", [""])[0]

        result = analyze_resume(resume, job)
        response = json.dumps(result).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), ResumeCheckerHandler)
    print("ATS Resume Checker is running at http://localhost:%s" % PORT)
    print("Press Ctrl+C to stop the server.")
    server.serve_forever()
