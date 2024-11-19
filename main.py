from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date
from typing import List, Optional
import firebase_admin
from firebase_admin import credentials, firestore
import os

# Inicializa Firebase
cred_path = "config/serviceAccountKey.json"


# Verifica que el archivo de credenciales exista
if not os.path.exists(cred_path):
    raise FileNotFoundError(f"El archivo de credenciales no se encuentra en: {cred_path}")

cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()

# Modelos Pydantic
class GastoComun(BaseModel):
    departamento_id: int
    departamento: int
    periodo: str
    monto: float
    pagado: bool = False
    fecha_pago: Optional[date] = None

class GenerarGastosRequest(BaseModel):
    año: int
    mes: Optional[int] = None
    departamentos: List[int]

class PagoRequest(BaseModel):
    departamento_id: int
    periodo: str
    fecha_pago: date


try:
    doc_ref = db.collection("test_collection").document("test_doc")
    doc_ref.set({"message": "Conexión exitosa"})
    print("Firebase conectado correctamente.")
except Exception as e:
    print(f"Error al conectar a Firebase: {e}")


# Endpoint para generar gastos comunes
@app.post("/generar-gastos/")
def generar_gastos(request: GenerarGastosRequest):
    gastos_generados = []
    try:
        for depto_id in request.departamentos:
            meses = [request.mes] if request.mes else range(1, 13)
            for mes in meses:
                periodo = f"{request.año}-{str(mes).zfill(2)}"
                doc_ref = db.collection("gastos_comunes").document(f"{depto_id}-{periodo}")
                doc = doc_ref.get()

                if doc.exists:
                    continue  # Si ya existe, pasa al siguiente

                gasto = {
                    "departamento_id": depto_id,
                    "departamento": depto_id,
                    "periodo": periodo,
                    "monto": 100.0,
                    "pagado": False,
                    "fecha_pago": None,
                }
                doc_ref.set(gasto)
                gastos_generados.append(gasto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar los gastos: {e}")
    
    return {"mensaje": "Gastos generados exitosamente", "gastos": gastos_generados}

# Endpoint para registrar un pago
@app.post("/pagar-gasto/")
def pagar_gasto(pago: PagoRequest):
    try:
        doc_ref = db.collection("gastos_comunes").document(f"{pago.departamento_id}-{pago.periodo}")
        doc = doc_ref.get()

        if not doc.exists:
            raise HTTPException(status_code=404, detail="Gasto no encontrado")

        gasto = doc.to_dict()

        if gasto["pagado"]:
            return {"mensaje": "Pago duplicado", "estado": "Pago duplicado"}

        gasto["pagado"] = True
        gasto["fecha_pago"] = pago.fecha_pago.isoformat()
        doc_ref.update(gasto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al registrar el pago: {e}")

    return {
        "mensaje": "Pago registrado correctamente",
        "departamento_id": pago.departamento_id,
        "periodo": pago.periodo,
        "fecha_pago": pago.fecha_pago,
    }

# Endpoint para ver pagos realizados
@app.get("/ver-pagos/")
def ver_pagos(departamento_id: Optional[int] = None, periodo: Optional[str] = None):
    try:
        query = db.collection("gastos_comunes").where("pagado", "==", True)

        if departamento_id:
            query = query.where("departamento_id", "==", departamento_id)
        if periodo:
            query = query.where("periodo", "==", periodo)

        docs = query.stream()
        pagos = [doc.to_dict() for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar los pagos: {e}")

    return {"pagos": pagos} if pagos else {"mensaje": "No se encontraron pagos para los parámetros proporcionados."}

# Endpoint para ver todos los gastos comunes
@app.get("/ver-gastos/")
def ver_gastos(departamento_id: Optional[int] = None, periodo: Optional[str] = None):
    try:
        query = db.collection("gastos_comunes")

        if departamento_id:
            query = query.where("departamento_id", "==", departamento_id)
        if periodo:
            query = query.where("periodo", "==", periodo)

        docs = query.stream()
        gastos = [doc.to_dict() for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar los gastos: {e}")

    return {"gastos": gastos} if gastos else {"mensaje": "No se encontraron gastos para los parámetros proporcionados."}

# Endpoint para eliminar todos los datos
@app.delete("/eliminar-todos/")
def eliminar_todos():
    try:
        docs = db.collection("gastos_comunes").stream()
        for doc in docs:
            doc.reference.delete()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar los datos: {e}")

    return {"mensaje": "Todos los datos han sido eliminados"}

# Endpoint para ver gastos no pagados
@app.get("/ver-gastos-no-pagados/")
def ver_gastos_no_pagados(departamento_id: Optional[int] = None, periodo: Optional[str] = None):
    try:
        query = db.collection("gastos_comunes").where("pagado", "==", False)

        if departamento_id:
            query = query.where("departamento_id", "==", departamento_id)
        if periodo:
            query = query.where("periodo", "==", periodo)

        docs = query.stream()
        gastos = [doc.to_dict() for doc in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar los gastos no pagados: {e}")

    return {"gastos": gastos} if gastos else {"mensaje": "No se encontraron gastos no pagados para los parámetros proporcionados."}
