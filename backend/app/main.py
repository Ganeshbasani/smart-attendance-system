from datetime import date, datetime, timezone
from pathlib import Path
from collections import Counter
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import Session
from .config import settings
from .db import Base, engine, get_db
from .models import *
from .schemas import *
from .security import get_current_user, require_roles, verify_password, create_access_token
from .seed import seed
from .services.intelligence import student_subject_intelligence
from .services.attendance import create_session, issue_qr, submit_qr_attendance
from .services.audit import audit

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed(db)
    finally:
        db.close()
    yield

app = FastAPI(title="AttendX API", version="2.0.0", description="Attendance Intelligence & Early Intervention Platform", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
@app.middleware("http")
async def security_headers(request, call_next):
    response=await call_next(request)
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="SAMEORIGIN"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]="camera=(self), geolocation=()"
    return response

Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.uploads_dir), name="uploads")

@app.get(f"{settings.api_prefix}/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(func.count(User.id)))
    return {"status":"healthy","database":"connected","time":datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}

@app.post(f"{settings.api_prefix}/auth/login", response_model=LoginOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    username=data.username.strip()
    cutoff=datetime.now(timezone.utc).replace(tzinfo=None).timestamp()-600
    attempts=db.scalars(select(LoginAttempt).where(LoginAttempt.username==username).order_by(desc(LoginAttempt.attempted_at)).limit(10)).all()
    recent_failures=sum(1 for a in attempts if not a.success and a.attempted_at.timestamp()>=cutoff)
    if recent_failures>=5:
        raise HTTPException(429, "Too many failed attempts. Please try again later.")
    user = db.scalar(select(User).where(User.username == username, User.active == True))
    ok=bool(user and verify_password(data.password, user.password_hash))
    db.add(LoginAttempt(username=username,success=ok));db.commit()
    if not ok:
        raise HTTPException(401, "Invalid username or password")
    token = create_access_token(user.id, user.role)
    audit(db, user.id, "login", "user", user.id)
    return {"access_token": token}

@app.get(f"{settings.api_prefix}/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.scalar(select(Student).where(Student.student_id == user.student_id)) if user.student_id else None
    return {"id":user.id,"username":user.username,"full_name":user.full_name,"role":user.role,"student_id":user.student_id,"department":db.scalar(select(Department).where(Department.id==user.department_id)).name if user.department_id else None,"section":student.section.name if student else None}

@app.get(f"{settings.api_prefix}/student/dashboard")
def student_dashboard(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    rows = student_subject_intelligence(db, user.student_id)
    notices = db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(desc(Notification.created_at)).limit(6)).all()
    return {"subjects": rows, "notifications":[{"id":n.id,"priority":n.priority,"title":n.title,"message":n.message,"read":bool(n.read_at)} for n in notices], "summary":{"safe":sum(r['state']=='Safe' for r in rows),"watch":sum(r['state']=='Watch' for r in rows),"risk":sum(r['state']=='At Risk' for r in rows),"critical":sum(r['state']=='Critical' for r in rows)}}

@app.get(f"{settings.api_prefix}/student/schedule")
def student_schedule(user:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    stu=db.scalar(select(Student).where(Student.student_id==user.student_id))
    if not stu: raise HTTPException(404,"Student profile not found")
    rows=db.execute(select(TimetableEntry,Subject,Section).join(Subject,TimetableEntry.subject_id==Subject.id).join(Section,TimetableEntry.section_id==Section.id).where(TimetableEntry.section_id==stu.section_id).order_by(TimetableEntry.weekday,TimetableEntry.start_time)).all()
    return [{"weekday":r.weekday,"start_time":r.start_time,"end_time":r.end_time,"room":r.room,"code":subj.code,"subject":subj.name,"section":sec.name} for r,subj,sec in rows]

@app.get(f"{settings.api_prefix}/student/history")
def student_history(user: User = Depends(require_roles("student")), db: Session = Depends(get_db)):
    rows = db.execute(select(AttendanceRecord, ClassSession, Subject).join(ClassSession, AttendanceRecord.session_id==ClassSession.id).join(Subject, ClassSession.subject_id==Subject.id).where(AttendanceRecord.student_id==user.student_id).order_by(desc(ClassSession.session_date), desc(AttendanceRecord.marked_at)).limit(80)).all()
    return [{"date":s.session_date,"subject":subj.name,"code":subj.code,"status":rec.status,"source":rec.source} for rec,s,subj in rows]

@app.get(f"{settings.api_prefix}/student/devices")
def devices(user: User=Depends(require_roles("student")), db: Session=Depends(get_db)):
    return [{"id":d.id,"label":d.label,"active":d.active,"last_seen":d.last_seen} for d in db.scalars(select(Device).where(Device.student_id==user.student_id).order_by(desc(Device.created_at))).all()]

@app.post(f"{settings.api_prefix}/student/devices/register")
def register_device(data:dict,user:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    device_id=str(data.get("device_id", ""))
    label=str(data.get("label", "This device"))[:80]
    if len(device_id)<8: raise HTTPException(400,"Device identifier is too short")
    existing=db.scalar(select(Device).where(Device.student_id==user.student_id,Device.device_hash==device_id))
    if existing:
        existing.active=True;existing.label=label;existing.last_seen=datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        db.add(Device(student_id=user.student_id,device_hash=device_id,label=label,active=True,last_seen=datetime.now(timezone.utc).replace(tzinfo=None)))
    db.commit();audit(db,user.id,"device.register","device",None,{"label":label});return {"success":True}

@app.post(f"{settings.api_prefix}/student/attendance/scan")
def scan(data: QRScanIn, user: User=Depends(require_roles("student")), db: Session=Depends(get_db)):
    try:
        rec = submit_qr_attendance(db, user.student_id, data.qr_payload, data.device_id)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    audit(db, user.id, "attendance.scan", "attendance", rec.id, {"source":"qr"})
    return {"success":True,"record_id":rec.id,"message":"Attendance verified and recorded"}

@app.get(f"{settings.api_prefix}/faculty/assignments")
def assignments(user: User=Depends(require_roles("faculty")), db: Session=Depends(get_db)):
    rows = db.execute(select(FacultyAssignment, Subject, Section).join(Subject, FacultyAssignment.subject_id==Subject.id).join(Section, FacultyAssignment.section_id==Section.id).where(FacultyAssignment.faculty_user_id==user.id)).all()
    return [{"subject_id":s.id,"subject":s.name,"code":s.code,"section_id":sec.id,"section":sec.name} for _,s,sec in rows]

@app.post(f"{settings.api_prefix}/faculty/sessions")
def new_session(data: SessionCreateIn, user: User=Depends(require_roles("faculty")), db: Session=Depends(get_db)):
    try: s = create_session(db, user.id, data.subject_id, data.section_id, data.session_date, data.start_time, data.end_time)
    except ValueError as exc: raise HTTPException(403, str(exc))
    audit(db, user.id, "session.create", "session", s.id)
    return {"id":s.id,"status":s.status,"subject_id":s.subject_id,"section_id":s.section_id}

@app.get(f"{settings.api_prefix}/faculty/sessions/{{session_id}}/qr")
def session_qr(session_id:int, user:User=Depends(require_roles("faculty")), db:Session=Depends(get_db)):
    s=db.get(ClassSession,session_id)
    if not s or s.faculty_user_id != user.id: raise HTTPException(404,"Session not found")
    return {"payload":issue_qr(s),"expires_in":settings.qr_ttl_seconds}

@app.get(f"{settings.api_prefix}/faculty/sessions")
def faculty_sessions(user:User=Depends(require_roles("faculty")), db:Session=Depends(get_db)):
    rows = db.execute(select(ClassSession,Subject,Section).join(Subject,ClassSession.subject_id==Subject.id).join(Section,ClassSession.section_id==Section.id).where(ClassSession.faculty_user_id==user.id).order_by(desc(ClassSession.session_date),desc(ClassSession.created_at)).limit(40)).all()
    out=[]
    for s,subj,sec in rows:
        total=db.scalar(select(func.count(AttendanceRecord.id)).where(AttendanceRecord.session_id==s.id)) or 0
        present=db.scalar(select(func.count(AttendanceRecord.id)).where(AttendanceRecord.session_id==s.id,AttendanceRecord.status=="Present")) or 0
        out.append({"id":s.id,"date":s.session_date,"subject":subj.name,"code":subj.code,"section":sec.name,"status":s.status,"present":present,"total":total,"rate":round((present/total*100),1) if total else 0})
    return out

@app.get(f"{settings.api_prefix}/faculty/risk")
def faculty_risk(user:User=Depends(require_roles("faculty")), db:Session=Depends(get_db)):
    rows=db.scalars(select(Student).where(Student.department_id==user.department_id)).all()
    out=[]
    for stu in rows:
        for r in student_subject_intelligence(db,stu.student_id):
            if r['state'] in ('At Risk','Critical','Watch'):
                out.append({"student_id":stu.student_id,"student":stu.name,**r})
    out.sort(key=lambda x:(x['state']!='Critical',x['state']!='At Risk',x['current_percent']))
    return out[:60]

@app.post(f"{settings.api_prefix}/faculty/sessions/{{session_id}}/close")
def close_session(session_id:int,user:User=Depends(require_roles("faculty")),db:Session=Depends(get_db)):
    s=db.get(ClassSession,session_id)
    if not s or s.faculty_user_id!=user.id: raise HTTPException(404,"Session not found")
    s.status="closed";db.commit();audit(db,user.id,"session.close","session",s.id);return {"success":True}

@app.get(f"{settings.api_prefix}/faculty/sessions/{{session_id}}/review")
def session_review(session_id:int,user:User=Depends(require_roles("faculty","hod","admin")),db:Session=Depends(get_db)):
    s=db.get(ClassSession,session_id)
    if not s: raise HTTPException(404,"Session not found")
    rows=db.execute(select(AttendanceRecord,Student).join(Student,AttendanceRecord.student_id==Student.student_id).where(AttendanceRecord.session_id==session_id)).all()
    statuses=Counter(r.status for r,_ in rows)
    timestamps=[r.marked_at for r,_ in rows if r.status=="Present"]
    burst=False
    if len(timestamps)>=10:
        timestamps=sorted(timestamps)
        burst=sum((timestamps[i]-timestamps[i-1]).total_seconds()<=1 for i in range(1,len(timestamps))) >= 8
    devices=Counter((r.device_id or "unknown") for r,_ in rows if r.device_id)
    anomalies=[]
    if burst: anomalies.append({"type":"fast-burst","severity":"high","evidence":"Multiple check-ins occurred within a very short interval."})
    if any(v>=4 for v in devices.values()): anomalies.append({"type":"shared-device","severity":"high","evidence":"A single device identifier was used for multiple identities."})
    return {"session":{"id":s.id,"status":s.status},"counts":dict(statuses),"anomalies":anomalies,"records":[{"student_id":st.student_id,"student":st.name,"status":r.status,"marked_at":r.marked_at,"source":r.source,"device_id":r.device_id} for r,st in rows]}

@app.post(f"{settings.api_prefix}/faculty/attendance/mark")
def faculty_mark(data:AttendanceMarkIn,user:User=Depends(require_roles("faculty")),db:Session=Depends(get_db)):
    raise HTTPException(410,"Use a live session workflow; direct arbitrary attendance marking is disabled in production mode.")

@app.get(f"{settings.api_prefix}/requests/corrections")
def correction_list(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    q=select(CorrectionRequest).order_by(desc(CorrectionRequest.created_at))
    if user.role=='student': q=q.where(CorrectionRequest.requested_by==user.id)
    return [{"id":r.id,"session_id":r.session_id,"student_id":r.student_id,"requested_status":r.requested_status,"reason":r.reason,"document_name":r.document_name,"status":r.status,"created_at":r.created_at} for r in db.scalars(q.limit(100)).all()]

@app.post(f"{settings.api_prefix}/requests/corrections")
def correction_create(data:CorrectionIn,user:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    s=db.get(ClassSession,data.session_id)
    if not s: raise HTTPException(404,"Session not found")
    rec=CorrectionRequest(session_id=s.id,student_id=user.student_id,requested_status=data.requested_status,reason=data.reason,document_name=data.document_name,requested_by=user.id)
    db.add(rec); db.commit(); db.refresh(rec); audit(db,user.id,"correction.submit","correction",rec.id)
    return {"id":rec.id,"status":rec.status}

@app.post(f"{settings.api_prefix}/requests/corrections/{{request_id}}/review")
def correction_review(request_id:int,data:ReviewIn,user:User=Depends(require_roles("faculty","hod","admin")),db:Session=Depends(get_db)):
    rec=db.get(CorrectionRequest,request_id)
    if not rec: raise HTTPException(404,"Request not found")
    rec.status=data.decision;rec.reviewed_by=user.id;rec.review_note=data.note;rec.reviewed_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit();audit(db,user.id,"correction.review","correction",rec.id,{"decision":data.decision});return {"success":True}

@app.get(f"{settings.api_prefix}/interventions")
def intervention_list(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    q=select(Intervention).order_by(desc(Intervention.created_at))
    if user.role=='student': q=q.where(Intervention.student_id==user.student_id)
    return [{"id":i.id,"student_id":i.student_id,"subject_id":i.subject_id,"trigger_type":i.trigger_type,"recommendation":i.recommendation,"owner_user_id":i.owner_user_id,"status":i.status,"due_date":i.due_date,"notes":i.notes,"outcome":i.outcome} for i in db.scalars(q.limit(100)).all()]

@app.post(f"{settings.api_prefix}/interventions")
def intervention_create(data:InterventionIn,user:User=Depends(require_roles("faculty","hod","admin")),db:Session=Depends(get_db)):
    i=Intervention(**data.model_dump()); db.add(i);db.commit();db.refresh(i);audit(db,user.id,"intervention.create","intervention",i.id);return {"id":i.id}

@app.patch(f"{settings.api_prefix}/interventions/{{intervention_id}}")
def intervention_update(intervention_id:int,data:InterventionUpdateIn,user:User=Depends(require_roles("faculty","hod","admin")),db:Session=Depends(get_db)):
    i=db.get(Intervention,intervention_id)
    if not i: raise HTTPException(404,"Intervention not found")
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(i,k,v)
    if i.status=='Resolved': i.resolved_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit();audit(db,user.id,"intervention.update","intervention",i.id,data.model_dump(exclude_unset=True));return {"success":True}

@app.post(f"{settings.api_prefix}/requests/condonation")
def condonation_create(data:CondonationIn,user:User=Depends(require_roles("student")),db:Session=Depends(get_db)):
    exists=db.scalar(select(Subject).where(Subject.id==data.subject_id))
    if not exists: raise HTTPException(404,"Subject not found")
    rec=CondonationRequest(student_id=user.student_id,subject_id=data.subject_id,reason=data.reason,document_name=data.document_name,requested_by=user.id)
    db.add(rec);db.commit();db.refresh(rec);audit(db,user.id,"condonation.submit","condonation",rec.id);return {"id":rec.id,"status":rec.status}

@app.get(f"{settings.api_prefix}/requests/condonation")
def condonation_list(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    q=select(CondonationRequest).order_by(desc(CondonationRequest.created_at))
    if user.role=='student': q=q.where(CondonationRequest.requested_by==user.id)
    return [{"id":r.id,"student_id":r.student_id,"subject_id":r.subject_id,"reason":r.reason,"document_name":r.document_name,"status":r.status,"created_at":r.created_at} for r in db.scalars(q.limit(100)).all()]

@app.post(f"{settings.api_prefix}/requests/condonation/{{request_id}}/review")
def condonation_review(request_id:int,data:ReviewIn,user:User=Depends(require_roles("hod","admin")),db:Session=Depends(get_db)):
    rec=db.get(CondonationRequest,request_id)
    if not rec: raise HTTPException(404,"Request not found")
    rec.status=data.decision;rec.reviewed_by=user.id;rec.review_note=data.note;rec.reviewed_at=datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit();audit(db,user.id,"condonation.review","condonation",rec.id,{"decision":data.decision});return {"success":True}

@app.post(f"{settings.api_prefix}/documents")
def upload_document(file:UploadFile=File(...),user:User=Depends(get_current_user)):
    safe_name=Path(file.filename or "document").name
    if Path(safe_name).suffix.lower() not in {".pdf",".png",".jpg",".jpeg"}: raise HTTPException(400,"Only PDF, PNG, JPG and JPEG files are allowed")
    import uuid
    target=Path(settings.uploads_dir)/f"{uuid.uuid4().hex}_{safe_name}"
    data=file.file.read()
    if len(data)>5*1024*1024: raise HTTPException(413,"Maximum document size is 5 MB")
    target.write_bytes(data)
    return {"document_name":safe_name,"stored_as":target.name}

@app.get(f"{settings.api_prefix}/notifications")
def notifications(user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(desc(Notification.created_at)).limit(100)).all()
    return [{"id":n.id,"priority":n.priority,"title":n.title,"message":n.message,"read":bool(n.read_at),"created_at":n.created_at} for n in rows]

@app.post(f"{settings.api_prefix}/notifications/{{notification_id}}/read")
def notification_read(notification_id:int,user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    n=db.get(Notification,notification_id)
    if not n or n.user_id!=user.id: raise HTTPException(404,"Notification not found")
    n.read_at=datetime.now(timezone.utc).replace(tzinfo=None);db.commit();return {"success":True}

@app.get(f"{settings.api_prefix}/admin/system-health")
def system_health(user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    counts={
        "students": db.scalar(select(func.count(Student.id))) or 0,
        "users": db.scalar(select(func.count(User.id))) or 0,
        "sessions": db.scalar(select(func.count(ClassSession.id))) or 0,
        "attendance_records": db.scalar(select(func.count(AttendanceRecord.id))) or 0,
        "audit_events": db.scalar(select(func.count(AuditLog.id))) or 0,
        "open_interventions": db.scalar(select(func.count(Intervention.id)).where(Intervention.status!='Resolved')) or 0,
    }
    return counts

@app.get(f"{settings.api_prefix}/admin/audit")
def admin_audit(user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(150)).all()
    return [{"id:r.id if False else 0" : ""}] if False else [{"id":r.id,"action":r.action,"entity_type":r.entity_type,"entity_id":r.entity_id,"created_at":r.created_at,"details":r.details_json} for r in rows]

@app.post(f"{settings.api_prefix}/admin/users/{{user_id}}/toggle")
def admin_toggle_user(user_id:int,user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    target=db.get(User,user_id)
    if not target: raise HTTPException(404,"User not found")
    if target.id==user.id: raise HTTPException(400,"You cannot disable your own admin account")
    target.active=not target.active;db.commit();audit(db,user.id,"user.toggle","user",target.id,{"active":target.active});return {"active":target.active}

@app.get(f"{settings.api_prefix}/admin/people")
def admin_people(user:User=Depends(require_roles("admin")),db:Session=Depends(get_db)):
    users=db.scalars(select(User).order_by(User.role,User.full_name)).all()
    students=db.scalars(select(Student).order_by(Student.name)).all()
    return {"users":[{"id":u.id,"username":u.username,"full_name":u.full_name,"role":u.role,"active":u.active} for u in users],"students":[{"student_id":s.student_id,"name":s.name,"section":s.section.name,"department":s.department.code} for s in students]}

@app.get(f"{settings.api_prefix}/hod/overview")
def hod_overview(user:User=Depends(require_roles("hod","admin")),db:Session=Depends(get_db)):
    students=db.scalars(select(Student).where(Student.department_id==user.department_id)).all() if user.role=='hod' else db.scalars(select(Student)).all()
    risk_rows=[]
    for st in students:
        risk_rows.extend([{**r,"student":st.name,"student_id":st.student_id} for r in student_subject_intelligence(db,st.student_id)])
    return {"total_students":len(students),"at_risk":sum(r['state'] in ('At Risk','Critical') for r in risk_rows),"critical":sum(r['state']=='Critical' for r in risk_rows),"distribution":Counter(r['state'] for r in risk_rows),"rows":risk_rows[:80]}

@app.post(f"{settings.api_prefix}/sync/events")
def sync_events(data:list[SyncEventIn],user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    accepted=0;rejected=0;duplicate=0
    for event in data:
        if db.scalar(select(SyncEvent).where(SyncEvent.client_event_id==event.client_event_id)):
            duplicate+=1;continue
        kind=event.payload.get("kind")
        se=SyncEvent(client_event_id=event.client_event_id,payload_json=str(event.payload),status='Pending');db.add(se);db.flush()
        try:
            if kind=="attendance_scan" and user.role=="student":
                import time
                submit_qr_attendance(db,user.student_id,event.payload["qr_payload"],event.payload["device_id"],allow_offline=True,queued_at=float(event.payload.get("queued_at",time.time())))
                se.status='Applied';se.applied_at=datetime.now(timezone.utc).replace(tzinfo=None);accepted+=1
            else:
                se.status='Applied';se.applied_at=datetime.now(timezone.utc).replace(tzinfo=None);accepted+=1
        except Exception as exc:
            se.status='Rejected';se.reason=str(exc);rejected+=1
            db.rollback();
            # Rollback erased the event insert; recreate the durable rejection record.
            se=SyncEvent(client_event_id=event.client_event_id,payload_json=str(event.payload),status='Rejected',reason=str(exc));db.add(se)
    db.commit();audit(db,user.id,"sync.batch","sync",None,{"accepted":accepted,"duplicate":duplicate,"rejected":rejected});return {"accepted":accepted,"duplicate":duplicate,"rejected":rejected}
