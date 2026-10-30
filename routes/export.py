from fastapi            import APIRouter, Depends, HTTPException
from fastapi.responses  import StreamingResponse 
from sqlalchemy.orm     import Session
from pydantic           import BaseModel
from typing             import List, Optional
import io
import json
from database.db        import get_db
from models.models      import Conversation, Company
from utils.auth         import verify_token
from utils.export       import export_to_excel, export_to_pdf

router = APIRouter(prefix="/export", tags=["Export"])


class ExportRequest(BaseModel):
    question     : str
    answer       : Optional[str] = ""
    sql_query    : Optional[str] = ""
    data         : List[dict]    = []
    format       : str           = "excel"    

@router.post("/download")
def download_export(
    data         : ExportRequest,
    db           : Session = Depends(get_db),
    current_user : dict    = Depends(verify_token)
):

    # Company name for report
    company = db.query(Company).filter(
        Company.id == current_user["company_id"]
    ).first()
    company_name = company.name if company else "Company"

    if data.format == "excel":
        file_bytes = export_to_excel(
            question     = data.question,
            sql_query    = data.sql_query,
            data         = data.data,
            company_name = company_name
        )
        
        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers    = {
                "Content-Disposition": 'attachment; filename="bi_results.xlsx"'
            }
        )

    elif data.format == "pdf":
        file_bytes = export_to_pdf(
            question     = data.question,
            answer       = data.answer,
            sql_query    = data.sql_query,
            data         = data.data,
            company_name = company_name
        )

        return StreamingResponse(
            io.BytesIO(file_bytes),
            media_type = "application/pdf",
            headers    = {
                "Content-Disposition": 'attachment; filename="bi_report.pdf"'
            }
        )

    else:
        raise HTTPException(
            status_code = 400,
            detail      = "Invalid format. Use 'excel' or 'pdf'"
        )