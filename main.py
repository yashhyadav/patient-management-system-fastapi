from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated, Literal, Optional
import json

app = FastAPI()


class Patient(BaseModel):
    id: Annotated[str, Field(..., description="ID of the patient", examples=["P001"])]
    name: Annotated[str, Field(..., description="Name of the patient", examples=["John Doe"])]
    city: Annotated[str, Field(..., description="City of the patient", examples=["New York"])]
    age: Annotated[int, Field(..., gt=0, lt=100, description="Age of the patient", examples=[30])]
    gender: Annotated[Literal['Male', 'Female', 'others'], Field(..., description="Gender of the patient")]
    height: Annotated[float, Field(..., gt=0, description="Height of the patient in cm")]
    weight: Annotated[float, Field(..., gt=0, description="Weight of the patient in kg")]

    @computed_field
    @property
    def bmi(self) -> float:
        return round(self.weight / (self.height / 100) ** 2, 2)

    @computed_field
    @property
    def verdict(self) -> str:
        if self.bmi < 18.5:
            return "Underweight"
        elif self.bmi < 25:
            return "Normal weight"
        elif self.bmi < 30:
            return "Overweight"
        else:
            return "Obese"


class PatientUpdate(BaseModel):
    name: Annotated[Optional[str], Field(default=None)]
    city: Annotated[Optional[str], Field(default=None)]
    age: Annotated[Optional[int], Field(default=None, gt=0, lt=100)]
    # Same allowed values as Patient so re-validation doesn't fail
    gender: Annotated[Optional[Literal['Male', 'Female', 'others']], Field(default=None)]
    height: Annotated[Optional[float], Field(default=None, gt=0)]
    weight: Annotated[Optional[float], Field(default=None, gt=0)]


def load_data():
    with open('patients.json', 'r') as f:
        return json.load(f)


def save_data(data):
    with open('patients.json', 'w') as f:
        json.dump(data, f, indent=4)


@app.get('/')
def hello():
    return {'message': 'Patient Management System API'}


@app.get('/about')
def about():
    return {
        'message': 'A fully functional API to manage patient records, appointments, and medical history. '
                   'This API allows healthcare providers to efficiently handle patient data, '
                   'schedule appointments, and maintain comprehensive medical records.'
    }


@app.get('/view')
def view():
    return load_data()


@app.get('/patient/{patient_id}')
def view_patient(
    patient_id: str = Path(..., description="The ID of the patient in the DB", examples=["P001"])
):
    data = load_data()
    if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail="Patient not found")


@app.get('/sort')
def sort_patients(
    sort_by: str = Query(..., description="Sort on the basis of height, weight or bmi"),
    order: str = Query(..., description="Sort order: asc or desc"),
):
    valid_fields = ['height', 'weight', 'bmi']

    if sort_by not in valid_fields:
        raise HTTPException(status_code=400, detail=f"Invalid field. Select from {valid_fields}")

    if order not in ['asc', 'desc']:
        raise HTTPException(status_code=400, detail="Invalid order. Select from ['asc', 'desc']")

    data = load_data()
    reverse = order == 'desc'

    return sorted(data.values(), key=lambda x: x.get(sort_by, 0), reverse=reverse)


@app.post('/create')
def create_patient(patient: Patient):
    data = load_data()

    if patient.id in data:
        raise HTTPException(status_code=400, detail="Patient ID already exists")

    # exclude must be a set (or dict) in Pydantic v2, not a list
    data[patient.id] = patient.model_dump(exclude={'id'})
    save_data(data)

    return JSONResponse(content={"message": "Patient created successfully"}, status_code=201)


@app.put('/update/{patient_id}')
def update_patient(patient_id: str, patient_update: PatientUpdate):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_patient_info = data[patient_id]

    # Only the fields the client actually sent
    updated_patient_info = patient_update.model_dump(exclude_unset=True)
    for key, value in updated_patient_info.items():
        existing_patient_info[key] = value

    # Re-validate so bmi and verdict are recalculated
    existing_patient_info['id'] = patient_id
    patient_pydantic_object = Patient(**existing_patient_info)

    data[patient_id] = patient_pydantic_object.model_dump(exclude={'id'})
    save_data(data)

    return JSONResponse(content={"message": "Patient updated successfully"}, status_code=200)


@app.delete('/delete/{patient_id}')
def delete_patient(patient_id: str):
    data = load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404, detail="Patient not found")

    del data[patient_id]
    save_data(data)

    return JSONResponse(content={"message": "Patient deleted successfully"}, status_code=200)