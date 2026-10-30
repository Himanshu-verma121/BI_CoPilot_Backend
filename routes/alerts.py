from fastapi         import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm  import Session
from pydantic        import BaseModel
from typing          import List, Optional
import json
from database.db     import get_db
from models.models   import Alert, DBConnection
from utils.auth      import verify_token
from ai.anomaly_detector import AnomalyDetector, DEFAULT_KPI_CONFIGS

router   = APIRouter(prefix="/alerts", tags=["Alerts"])
detector = AnomalyDetector()


# Anomaly Detection 
@router.post("/detect/{connection_id}")
def run_detection(
    connection_id   : int,
    background_tasks: BackgroundTasks,     # runs task in background
    db              : Session = Depends(get_db),
    current_user    : dict    = Depends(verify_token)
):
    
    company_id = current_user["company_id"]

    connection = db.query(DBConnection).filter(
        DBConnection.id         == connection_id,
        DBConnection.company_id == company_id
    ).first()

    if not connection:
        return {"error": "Connection not found"}

    if connection.db_type == "mysql":
        url = f"mysql+pymysql://{connection.username}:{connection.password_enc}@{connection.host}:{connection.port}/{connection.db_name}"
    elif connection.db_type == "postgresql":
        url = f"postgresql://{connection.username}:{connection.password_enc}@{connection.host}:{connection.port}/{connection.db_name}"
    else:
        url = f"sqlite:///{connection.db_name}"

    background_tasks.add_task(
        run_detection_task,
        company_id    = company_id,
        connection_url = url,
        db            = db
    )

    return {
        "message": "Anomaly detection started in background. Check alerts in 30-60 seconds.",
        "status" : "running"
    }


def run_detection_task(company_id: int, connection_url: str, db: Session):
    try:
        anomalies = detector.detect_anomalies(
            company_id     = company_id,
            connection_url = connection_url,
            kpi_configs    = DEFAULT_KPI_CONFIGS
        )

        for anomaly in anomalies:
            alert = Alert(
                company_id         = company_id,
                kpi_name           = anomaly["kpi_name"],
                current_value      = str(anomaly["current_value"]),
                historical_value   = str(anomaly["historical_value"]),
                pct_change         = str(anomaly["pct_change"]),
                severity           = anomaly["severity"],
                message            = anomaly["message"],
                possible_causes    = json.dumps(anomaly["possible_causes"]),
                recommended_action = anomaly["recommended_action"]
            )
            db.add(alert)

        db.commit()
        print(f"Detection complete. Found {len(anomalies)} anomalies.")

    except Exception as e:
        print(f"Detection error: {e}")


# Alerts
@router.get("/list")
def get_alerts(
    unread_only  : bool    = False,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    query = db.query(Alert).filter(
        Alert.company_id == current_user["company_id"]
    )

    if unread_only:
        query = query.filter(Alert.is_read == False)

    alerts = query.order_by(Alert.created_at.desc()).limit(50).all()

    return {
        "alerts": [
            {
                "id"                : a.id,
                "kpi_name"          : a.kpi_name,
                "current_value"     : a.current_value,
                "historical_value"  : a.historical_value,
                "pct_change"        : a.pct_change,
                "severity"          : a.severity,
                "message"           : a.message,
                "possible_causes"   : json.loads(a.possible_causes or "[]"),
                "recommended_action": a.recommended_action,
                "is_read"           : a.is_read,
                "created_at"        : a.created_at.isoformat()
            }
            for a in alerts
        ],
        "total"       : len(alerts),
        "unread_count": sum(1 for a in alerts if not a.is_read)
    }


# Mark Alert as Read 
@router.patch("/{alert_id}/read")
def mark_as_read(
    alert_id     : int,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):
    """Mark a specific alert as read."""
    alert = db.query(Alert).filter(
        Alert.id         == alert_id,
        Alert.company_id == current_user["company_id"]
    ).first()

    if not alert:
        return {"error": "Alert not found"}

    alert.is_read = True
    db.commit()
    return {"message": "Alert marked as read"}