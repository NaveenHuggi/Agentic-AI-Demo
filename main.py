"""
Inbox Intelligence Agent — Web Dashboard
=========================================
This is the main FastAPI server that provides the web-based UI.
It uses the RULE-BASED analysis as the baseline.
The session demos (session_1/ through session_4/) progressively
replace this logic with LLM-powered intelligence.

Run:  uvicorn main:app --reload
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from utils.gmail_utils import fetch_recent_emails
from utils.calendar_utils import create_calendar_event
from utils.analysis import analyze_inbox

app = FastAPI(title="Inbox Intelligence Agent")

# Cache the last analysis so /schedule uses the exact same result
LAST_ANALYSIS: dict[str, Any] | None = None


# ============================================================
# UI
# ============================================================
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Inbox Intelligence Agent</title>
<style>
:root{
  --bg:#081120;
  --panel:#1c2940;
  --panel2:#22314d;
  --text:#f4f7fb;
  --muted:#b7c4dd;
  --green:#22c55e;
  --red:#ef4444;
  --blue:#60a5fa;
  --chip:#0f1a2f;
}
*{box-sizing:border-box}
body{
  margin:0;
  font-family:Arial, sans-serif;
  background:linear-gradient(135deg,#07101d,#0c1830 60%, #0a1430);
  color:var(--text);
}
.wrapper{
  max-width:1100px;
  margin:0 auto;
  padding:28px;
}
h1{
  margin:0 0 18px 0;
  font-size:42px;
}
.toolbar{
  display:flex;
  gap:12px;
  flex-wrap:wrap;
  margin-bottom:20px;
}
button{
  border:none;
  border-radius:12px;
  padding:12px 18px;
  font-weight:700;
  cursor:pointer;
}
.primary{background:var(--green); color:#04130b;}
.secondary{background:var(--blue); color:#07111f;}
.card{
  background:var(--panel);
  border-radius:20px;
  padding:22px;
  margin-top:18px;
}
.grid{
  display:grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap:18px;
}
.section-title{
  margin:0 0 12px 0;
  font-size:28px;
}
.muted{color:var(--muted)}
.kpis{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:10px;
  margin:14px 0 20px;
}
.kpi{
  background:var(--panel2);
  border-radius:14px;
  padding:14px;
  text-align:center;
}
.kpi .num{font-size:28px;font-weight:800}
.summary-box{
  line-height:1.6;
  color:var(--text);
  font-size:17px;
}
.urgent-list{
  margin:0;
  padding-left:20px;
}
.urgent-list li{margin:8px 0}
.urgent-item{color:var(--red); font-weight:700}
.good{color:var(--green); font-weight:700}
.email-list{
  display:flex;
  flex-direction:column;
  gap:12px;
}
.email-item{
  background:var(--panel2);
  border-radius:14px;
  padding:14px;
}
.email-item h4{
  margin:0 0 6px 0;
  font-size:17px;
}
.email-meta{
  font-size:13px;
  color:var(--muted);
  margin-bottom:8px;
}
.chip{
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  background:var(--chip);
  font-size:12px;
  margin-bottom:8px;
}
.chip.meeting{color:#facc15}
.chip.urgent{color:#fb7185}
.chip.info{color:#93c5fd}
.chip.task{color:#c4b5fd}
#status{margin-top:8px;color:var(--muted)}
@media (max-width: 900px){
  .grid{grid-template-columns:1fr}
  .kpis{grid-template-columns:repeat(2,1fr)}
  h1{font-size:32px}
}
</style>
</head>
<body>
<div class="wrapper">
  <h1>📧 Inbox Intelligence Agent</h1>
  <div class="toolbar">
    <button class="primary" onclick="analyzeInbox()">Analyze Inbox</button>
    <button class="secondary" id="scheduleBtn" onclick="scheduleMeeting()" style="display:none;">📅 Schedule Meeting + Send Invites</button>
  </div>
  <div id="status">Ready.</div>

  <div class="grid">
    <div class="card">
      <h2 class="section-title">Overall Summary</h2>
      <div id="overallSummary" class="summary-box">Click "Analyze Inbox".</div>

      <div class="kpis">
        <div class="kpi"><div class="num" id="meetingCount">0</div><div>Meeting</div></div>
        <div class="kpi"><div class="num" id="urgentCount">0</div><div>Urgent</div></div>
        <div class="kpi"><div class="num" id="infoCount">0</div><div>Info</div></div>
        <div class="kpi"><div class="num" id="taskCount">0</div><div>Task</div></div>
      </div>

      <h3>Urgent Emails</h3>
      <ul id="urgentList" class="urgent-list"></ul>

      <h3>Suggested Action</h3>
      <div id="suggestedAction" class="summary-box muted"></div>

      <h3>Detected Meeting</h3>
      <div id="meetingInfo" class="summary-box muted">No meeting detected.</div>
    </div>

    <div class="card">
      <h2 class="section-title">10 Email Summaries</h2>
      <div id="emailSummaries" class="email-list"></div>
    </div>
  </div>
</div>

<script>
let latestAnalysis = null;

function setStatus(msg){
  document.getElementById("status").innerText = msg;
}

function escapeHtml(text){
  const div = document.createElement("div");
  div.innerText = text ?? "";
  return div.innerHTML;
}

async function analyzeInbox(){
  setStatus("Analyzing inbox...");
  document.getElementById("scheduleBtn").style.display = "none";

  try{
    const res = await fetch("/analyze", {method:"POST"});
    const data = await res.json();

    if(!res.ok){
      throw new Error(data.error || "Analysis failed");
    }

    latestAnalysis = data;
    renderAnalysis(data);
    setStatus("Analysis completed.");
  }catch(err){
    setStatus("Error: " + err.message);
  }
}

function renderAnalysis(data){
  document.getElementById("overallSummary").innerText = data.inbox_summary || "No summary available.";
  document.getElementById("meetingCount").innerText = data.categories?.meeting ?? 0;
  document.getElementById("urgentCount").innerText = data.categories?.urgent ?? 0;
  document.getElementById("infoCount").innerText = data.categories?.info ?? 0;
  document.getElementById("taskCount").innerText = data.categories?.task ?? 0;
  document.getElementById("suggestedAction").innerText = data.suggested_action || "No action suggested.";

  const urgentList = document.getElementById("urgentList");
  urgentList.innerHTML = "";
  if(Array.isArray(data.urgent_emails) && data.urgent_emails.length){
    data.urgent_emails.forEach(item => {
      const li = document.createElement("li");
      li.className = "urgent-item";
      li.innerText = item;
      urgentList.appendChild(li);
    });
  } else {
    const li = document.createElement("li");
    li.className = "good";
    li.innerText = "No urgent emails 🎉";
    urgentList.appendChild(li);
  }

  const meetingInfo = document.getElementById("meetingInfo");
  if(data.meeting_time && data.meeting_time !== "NONE"){
    const attendees = (data.meeting_attendees || []).join(", ");
    meetingInfo.innerText = `Meeting detected at ${data.meeting_time}. Attendees: ${attendees || "No attendee emails detected."}`;
    document.getElementById("scheduleBtn").style.display = "inline-block";
  } else {
    meetingInfo.innerText = "No meeting detected.";
    document.getElementById("scheduleBtn").style.display = "none";
  }

  const list = document.getElementById("emailSummaries");
  list.innerHTML = "";
  (data.email_summaries || []).forEach(item => {
    const div = document.createElement("div");
    div.className = "email-item";
    div.innerHTML = `
      <div class="chip ${escapeHtml(item.category || "info")}">${escapeHtml((item.category || "info").toUpperCase())}</div>
      <h4>${escapeHtml(item.subject || "No Subject")}</h4>
      <div class="email-meta">${escapeHtml(item.from_email || "Unknown sender")}</div>
      <div>${escapeHtml(item.summary || "No summary available.")}</div>
    `;
    list.appendChild(div);
  });
}

async function scheduleMeeting(){
  if(!latestAnalysis){
    setStatus("Analyze inbox first.");
    return;
  }

  setStatus("Scheduling meeting and sending invites...");
  try{
    const res = await fetch("/schedule", {method:"POST"});
    const data = await res.json();

    if(!res.ok){
      throw new Error(data.error || "Scheduling failed");
    }

    setStatus("Meeting scheduled and invites sent.");
    if(data.link){
      window.open(data.link, "_blank");
    }
  }catch(err){
    setStatus("Error: " + err.message);
  }
}
</script>
</body>
</html>
"""


# ============================================================
# ROUTES
# ============================================================
@app.post("/analyze")
def analyze():
    global LAST_ANALYSIS
    try:
        emails = fetch_recent_emails(limit=10)
        LAST_ANALYSIS = analyze_inbox(emails)
        return JSONResponse(LAST_ANALYSIS)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/schedule")
def schedule():
    global LAST_ANALYSIS
    try:
        if not LAST_ANALYSIS:
            return JSONResponse({"error": "Analyze inbox first."}, status_code=400)

        meeting_time = LAST_ANALYSIS.get("meeting_time", "NONE")
        attendees = LAST_ANALYSIS.get("meeting_attendees", [])
        title = LAST_ANALYSIS.get("meeting_subject", "AI Scheduled Meeting")

        if meeting_time == "NONE":
            return JSONResponse({"error": "No meeting detected to schedule."}, status_code=400)

        link = create_calendar_event(meeting_time, attendees, title)
        return JSONResponse({"ok": True, "link": link})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


