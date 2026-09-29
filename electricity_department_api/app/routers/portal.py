"""
Public portal routes for the Electricity Department website (UI only).

Read-only views over the department's own tables, in the same spirit as
/api/electricity/public-list: no machine credentials, no writes. The
machine-to-machine contract used by the interoperability platform
(/applications, /verify, /status) is untouched.
"""
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.electricity import ElectricityApplication, ElectricityConnection

router = APIRouter(prefix="/api/electricity/portal", tags=["Public Portal (UI)"])

# Distribution zones -> circles (districts) -> divisions (talukas).
# Every district/taluka in the seed data appears here, so each seeded
# application can be reached from the zone picker.
ZONES: List[Dict[str, Any]] = [
    {"id": "pune", "name_mr": "पुणे परिमंडळ", "name_en": "Pune Zone", "circles": [
        {"name_en": "Pune", "name_mr": "पुणे", "divisions": [
            {"name_en": "Haveli", "name_mr": "हवेली"}, {"name_en": "Khed", "name_mr": "खेड"},
            {"name_en": "Maval", "name_mr": "मावळ"}, {"name_en": "Daund", "name_mr": "दौंड"},
            {"name_en": "Shirur", "name_mr": "शिरूर"}, {"name_en": "Mulshi", "name_mr": "मुळशी"}]},
        {"name_en": "Satara", "name_mr": "सातारा", "divisions": [
            {"name_en": "Satara", "name_mr": "सातारा"}, {"name_en": "Karad", "name_mr": "कराड"}]},
    ]},
    {"id": "konkan", "name_mr": "कोकण परिमंडळ", "name_en": "Konkan Zone", "circles": [
        {"name_en": "Thane", "name_mr": "ठाणे", "divisions": [
            {"name_en": "Bhiwandi", "name_mr": "भिवंडी"}, {"name_en": "Kalyan", "name_mr": "कल्याण"}]},
        {"name_en": "Raigad", "name_mr": "रायगड", "divisions": [
            {"name_en": "Panvel", "name_mr": "पनवेल"}, {"name_en": "Pen", "name_mr": "पेण"}]},
    ]},
    {"id": "nashik", "name_mr": "नाशिक परिमंडळ", "name_en": "Nashik Zone", "circles": [
        {"name_en": "Nashik", "name_mr": "नाशिक", "divisions": [
            {"name_en": "Sinnar", "name_mr": "सिन्नर"}, {"name_en": "Niphad", "name_mr": "निफाड"}]},
        {"name_en": "Ahilyanagar", "name_mr": "अहिल्यानगर", "divisions": [
            {"name_en": "Shrirampur", "name_mr": "श्रीरामपूर"}]},
    ]},
    {"id": "sambhajinagar", "name_mr": "छत्रपती संभाजीनगर परिमंडळ", "name_en": "Chhatrapati Sambhajinagar Zone", "circles": [
        {"name_en": "Chhatrapati Sambhajinagar", "name_mr": "छत्रपती संभाजीनगर", "divisions": [
            {"name_en": "Gangapur", "name_mr": "गंगापूर"}, {"name_en": "Paithan", "name_mr": "पैठण"}]},
        {"name_en": "Jalna", "name_mr": "जालना", "divisions": [{"name_en": "Jalna", "name_mr": "जालना"}]},
    ]},
    {"id": "nagpur", "name_mr": "नागपूर परिमंडळ", "name_en": "Nagpur Zone", "circles": [
        {"name_en": "Nagpur", "name_mr": "नागपूर", "divisions": [
            {"name_en": "Nagpur Rural", "name_mr": "नागपूर ग्रामीण"}, {"name_en": "Hingna", "name_mr": "हिंगणा"}]},
        {"name_en": "Wardha", "name_mr": "वर्धा", "divisions": [{"name_en": "Wardha", "name_mr": "वर्धा"}]},
    ]},
]

# Labels for the department's own status values (no new statuses invented).
STATUS_LABELS = {
    "SUBMITTED": ("अर्ज प्राप्त", "Submitted"),
    "UNDER_SCRUTINY": ("कागदपत्र छाननी सुरू", "Under document scrutiny"),
    "PENDING": ("प्रलंबित", "Pending"),
    "UNDER_INSPECTION": ("स्थळ तपासणी सुरू", "Site inspection in progress"),
    "APPROVED": ("मंजूर", "Approved"),
    "REJECTED": ("नामंजूर", "Rejected"),
}


def _summary(a: ElectricityApplication) -> Dict[str, Any]:
    mr, en = STATUS_LABELS.get(a.application_status, (a.application_status, a.application_status))
    return {
        "application_number": a.application_number,
        "consumer_number": a.consumer_number,
        "applicant_name": a.applicant_name,
        "applicant_pan": a.applicant_pan,
        "district": a.district,
        "taluka": a.taluka,
        "village": a.village,
        "supply_category": a.supply_category,
        "connection_type": a.connection_type,
        "requested_load": f"{a.requested_load} {a.requested_load_unit}",
        "sanctioned_load": f"{a.sanctioned_load} {a.sanctioned_load_unit}" if a.sanctioned_load else None,
        "application_status": a.application_status,
        "status_mr": mr,
        "status_en": en,
        "inspection_status": a.inspection_status,
        "meter_status": a.meter_status,
        "connection_status": a.connection_status,
        "security_deposit_status": a.security_deposit_status,
        "outstanding_dues": bool(a.outstanding_dues),
        "application_date": a.application_date.isoformat() if a.application_date else None,
        "last_updated": a.last_updated.isoformat() if a.last_updated else None,
        "rejection_reason": a.rejection_reason,
        "objection_reason": a.objection_reason,
    }


def _stages(a: ElectricityApplication) -> List[Dict[str, Any]]:
    """Application progress, derived only from the fields stored on the record.

    Each stage is one of: done, current, pending, failed, not_required.
    """
    rejected = a.application_status == "REJECTED"
    approved = a.application_status == "APPROVED"
    insp = a.inspection_status
    dep = a.security_deposit_status

    def st(done: bool, current: bool = False, failed: bool = False, not_required: bool = False) -> str:
        if failed:
            return "failed"
        if not_required:
            return "not_required"
        if done:
            return "done"
        return "current" if current else "pending"

    scrutiny_done = a.application_status not in ("SUBMITTED", "UNDER_SCRUTINY")
    stages = [
        {"key": "submitted", "mr": "अर्ज दाखल", "en": "Application submitted", "state": "done",
         "detail": a.application_date.strftime("%d-%m-%Y") if a.application_date else None},
        {"key": "scrutiny", "mr": "कागदपत्र छाननी", "en": "Document scrutiny",
         "state": st(scrutiny_done, current=not scrutiny_done)},
        {"key": "inspection", "mr": "स्थळ तपासणी", "en": "Site inspection",
         "state": st(insp == "COMPLETED", current=insp in ("PENDING", "IN_PROGRESS") and scrutiny_done,
                     failed=insp == "FAILED", not_required=insp == "NOT_REQUIRED"),
         "detail": a.inspection_reference},
        {"key": "sanction", "mr": "भार मंजुरी", "en": "Load sanction",
         "state": st(approved, current=insp == "COMPLETED" and not approved and not rejected, failed=rejected),
         "detail": (f"{a.sanctioned_load} {a.sanctioned_load_unit}" if approved else a.rejection_reason)},
        {"key": "deposit", "mr": "सुरक्षा ठेव", "en": "Security deposit",
         "state": st(dep in ("PAID", "WAIVED"), current=approved and dep == "PENDING", not_required=dep == "NOT_REQUIRED")},
        {"key": "meter", "mr": "मीटर बसवणी", "en": "Meter installation",
         "state": st(a.meter_status == "INSTALLED", current=approved and dep in ("PAID", "WAIVED") and a.meter_status != "INSTALLED")},
        {"key": "energised", "mr": "वीजपुरवठा सुरू", "en": "Supply energised",
         "state": st(a.connection_status == "ENERGIZED",
                     current=a.meter_status == "INSTALLED" and a.connection_status != "ENERGIZED"),
         "detail": ("थकबाकी प्रलंबित (Outstanding dues)" if a.outstanding_dues and a.connection_status != "ENERGIZED" else None)},
    ]
    return stages


@router.get("/zones", summary="Distribution zones, circles (districts) and divisions (talukas)")
async def get_zones():
    return {"zones": ZONES}


@router.get("/applications", summary="Search new-connection applications")
async def search_applications(
    district: Optional[str] = Query(None),
    taluka: Optional[str] = Query(None),
    search_type: str = Query("application", pattern="^(application|consumer|pan|name|all)$"),
    query: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ElectricityApplication)
    if district:
        q = q.filter(ElectricityApplication.district.ilike(district))
    if taluka:
        q = q.filter(ElectricityApplication.taluka.ilike(taluka))
    text = (query or "").strip()
    if text and search_type != "all":
        if search_type == "application":
            q = q.filter(ElectricityApplication.application_number.ilike(f"%{text}%"))
        elif search_type == "consumer":
            q = q.filter(ElectricityApplication.consumer_number.ilike(f"%{text}%"))
        elif search_type == "pan":
            q = q.filter(ElectricityApplication.applicant_pan == text.upper())
        elif search_type == "name":
            q = q.filter(ElectricityApplication.applicant_name.ilike(f"%{text}%"))
    rows = q.order_by(ElectricityApplication.id.asc()).all()
    return {"count": len(rows), "results": [_summary(a) for a in rows]}


@router.get("/applications/{application_number}/tracker", summary="Application progress tracker")
async def application_tracker(application_number: str, db: Session = Depends(get_db)):
    a = db.query(ElectricityApplication).filter(
        ElectricityApplication.application_number == application_number.strip().upper()
    ).first()
    if not a:
        raise HTTPException(status_code=404, detail=f"No application found with number {application_number}")
    return {"application": _summary(a), "stages": _stages(a)}


@router.get("/connections", summary="Look up existing consumer connections")
async def search_connections(
    search_type: str = Query("consumer", pattern="^(consumer|pan|meter)$"),
    query: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    text = query.strip()
    q = db.query(ElectricityConnection)
    if search_type == "consumer":
        q = q.filter(ElectricityConnection.consumer_number.ilike(f"%{text}%"))
    elif search_type == "pan":
        q = q.filter(ElectricityConnection.applicant_pan == text.upper())
    else:
        q = q.filter(ElectricityConnection.meter_number.ilike(f"%{text}%"))
    return {"results": [
        {
            "consumer_number": c.consumer_number,
            "application_number": c.application_number,
            "applicant_name": c.applicant_name,
            "applicant_pan": c.applicant_pan,
            "premises_address": c.premises_address,
            "supply_category": c.supply_category,
            "connection_type": c.connection_type,
            "sanctioned_load": f"{c.sanctioned_load} {c.sanctioned_load_unit}",
            "meter_number": c.meter_number,
            "meter_status": c.meter_status,
            "connection_status": c.connection_status,
            "outstanding_dues": bool(c.outstanding_dues),
            "energization_date": c.energization_date.isoformat() if c.energization_date else None,
        }
        for c in q.order_by(ElectricityConnection.id.asc()).all()
    ]}


@router.get("/supply-guide", summary="Which supply category a requested load falls under")
async def supply_guide(load_kw: float = Query(..., gt=0)):
    # Same threshold the Samanvay questionnaire uses: 100 kW and above is high tension.
    ht = load_kw >= 100
    return {
        "load_kw": load_kw,
        "category": "HT-IND" if ht else "LT-IND",
        "category_mr": "उच्च दाब (HT) औद्योगिक" if ht else "लघु दाब (LT) औद्योगिक",
        "category_en": "High tension (HT) industrial" if ht else "Low tension (LT) industrial",
        "note_mr": ("१०० kW किंवा अधिक भारासाठी उच्च दाब जोडणी व व्यवहार्यता तपासणी आवश्यक. पुरवठा दाब (11/22/33 kV) विभाग तपासणीनंतर ठरवतो."
                    if ht else "१०० kW पेक्षा कमी भारासाठी लघु दाब (415 V, थ्री-फेज) जोडणी."),
        "note_en": ("Loads of 100 kW or more need a high-tension connection and a feasibility check. The supply voltage (11/22/33 kV) is decided by the department after inspection."
                    if ht else "Loads under 100 kW get a low-tension (415 V, three-phase) connection."),
        "documents": [
            {"mr": "अर्जदाराचा पॅन / ओळखपत्र", "en": "Applicant PAN / identity proof"},
            {"mr": "जागेच्या मालकीचा किंवा भाडेपट्ट्याचा पुरावा (७/१२ उतारा)", "en": "Proof of ownership or lease of the premises (7/12 extract)"},
            {"mr": "मंजूर भार व जोडलेल्या यंत्रांची यादी", "en": "Requested load and list of connected machinery"},
        ] + ([{"mr": "विद्युत निरीक्षकाचे मंजुरी पत्र", "en": "Electrical Inspector's approval of the installation"}] if ht else []),
    }
