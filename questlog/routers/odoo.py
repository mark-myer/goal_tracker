from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from questlog import models as schemas
from questlog.crypto import encrypt_value
from questlog.database import OdooConnection, get_db
from questlog.services.odoo_fetcher import browse_models, get_numeric_fields, test_connection

router = APIRouter(prefix="/odoo", tags=["odoo"])


@router.get("/connections", response_model=list[schemas.OdooConnectionOut])
def list_connections(db: Session = Depends(get_db)):
    return db.query(OdooConnection).all()


@router.post("/connections", response_model=schemas.OdooConnectionOut)
def create_connection(payload: schemas.OdooConnectionCreate, db: Session = Depends(get_db)):
    connection = OdooConnection(
        name=payload.name,
        url=payload.url,
        db=payload.db,
        user=payload.user,
        api_key=encrypt_value(payload.api_key),
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.post("/connections/{connection_id}/test")
def test_odoo_connection(connection_id: int, db: Session = Depends(get_db)):
    connection = db.query(OdooConnection).filter(OdooConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return test_connection(connection)


@router.get("/connections/{connection_id}/models")
def models(connection_id: int, db: Session = Depends(get_db)):
    connection = db.query(OdooConnection).filter(OdooConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return browse_models(connection)


@router.get("/connections/{connection_id}/fields")
def fields(connection_id: int, model: str = Query(...), db: Session = Depends(get_db)):
    connection = db.query(OdooConnection).filter(OdooConnection.id == connection_id).first()
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    return get_numeric_fields(connection, model)
