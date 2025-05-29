import os
import json
import subprocess
from jinja2 import Template
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pyppeteer import launch
from pydantic import BaseModel
from typing import List,Dict,Any

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StudentData(BaseModel):
    studentinfo: List[Dict[str, Any]] = []
    studentname: str = ""
    dob: str = ""
    studentemail: str = ""
    studentmobilenumber: str = ""
    studentaddress: str = ""
    fathername: str = ""
    fatheroccupation: str = ""
    mothername: str = ""
    motheroccupation: str = ""
    city: str = ""
    degreeinfo: List[Dict[str, str]] = []
    degreecollege: str = ""
    degreeyearofpass: str = ""
    intercollegename: str = ""
    interboard: str = ""
    interpercentage: str = ""
    interyearofpass: str = ""
    sscschoolname: str = ""
    sscboard: str = ""
    sscgpa: str = ""
    sscyearofpass: str = ""
    skillset: List[str] = []
    projectinfo: List[Dict[str, str]] = []
    experienceinfo: List[Dict[str, Any]] = []
    coursecertification: List[str] = []
    language:List[str] = []

try:
    with open("drive_info.json", "r", encoding="utf-8") as f:
        drive_info = json.load(f)
        drive_name = drive_info.get("drive_name", "DefaultDrive")
except Exception as e:
    print("Error loading drive_info.json:", e)
    raise SystemExit(1)

try:
    with open("resume_template.html", "r", encoding="utf-8") as f:
        template_content = f.read()
        template = Template(template_content)
except FileNotFoundError:
    print("Error: 'resume_template.html' not found.")
    raise SystemExit(1)

async def init_browser():
    return await launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu'
        ],
        executablePath="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    )

async def generate_pdf(page, html_content):
    await page.setContent(html_content)
    await page.waitFor(500)
    return await page.pdf({
        'printBackground': True,
        'format': 'A4',
        'margin': {'top': '20mm', 'right': '20mm', 'bottom': '20mm', 'left': '20mm'},
        'preferCSSPageSize': True
    })

@app.on_event("startup")
async def startup_event():
    app.state.browser = await init_browser()

@app.on_event("shutdown")
async def shutdown_event():
    await app.state.browser.close()

@app.post("/gr")
async def generate_resume_from_json(student_info: List[StudentData]):
    page = None
    try:
        if not student_info or len(student_info) == 0:
            raise HTTPException(status_code=400, detail="Empty student data list")

        student_data = student_info[0].dict()
        student_name = student_data.get("studentname", "UnknownStudent")
        city =student_data.get("city","unknown city")
        safe_student_name = student_name.replace(" ", "_")

        if student_data.get("degreeinfo"):
            try:
                cgpas = [float(d.get("percentage", 0)) for d in student_data["degreeinfo"] if d.get("percentage")]
                avg_cgpa = sum(cgpas) / len(cgpas) if cgpas else 0
                student_data["degreeavgcgpa"] = f"{avg_cgpa:.2f}"
            except Exception as e:
                print(f"Error calculating average CGPA: {e}")
                student_data["degreeavgcgpa"] = "N/A"

        prompt = f"""
            Write a short, professional resume objective in 2-3 sentences based strictly on the following details:
            Name: {student_data.get('studentname', '')}
            Degree: {student_data.get('degreecollege', '')} ({student_data.get('degreeyearofpass', '')})
            CGPA: {student_data.get('degreeavgcgpa', '')}
            Skills: {", ".join(student_data.get('skillset', []))}
            Projects: {", ".join([p.get('name', '') for p in student_data.get('projectinfo', [])])}
            Experience: {", ".join([exp.get('company', '') for exp in student_data.get('experienceinfo', [])])}

            Respond with only the resume objective text. Do not include any introductions, explanations, or formatting outside the objective itself.
        """

        result = subprocess.run(
            ["ollama", "run", "llama3", prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        student_data["objective"] = result.stdout.strip() if result.returncode == 0 else (
            f"Recent {student_data.get('degreecollege', '').split(',')[0].strip()} graduate. "
            f"Skilled in {', '.join(student_data.get('skillset', ['']))}. "
            f"Seeking opportunities to apply my knowledge and grow professionally."
        )
        lang = student_data.get("language", [])
        lang = ", ".join(lang)

        address = student_data.get("studentaddress", "")
        if address.endswith(city):
            formatted_address = address
        else:
            formatted_address = f"{address}, {city}" if address else city

        formatted_certificates = student_data.get("coursecertification", [])
        formatted_certificates = ", ".join(formatted_certificates)

        data_for_template = {
            "studentname": student_data.get("studentname", ""),
            "studentmobilenumber": student_data.get("studentmobilenumber", ""),
            "studentemail": student_data.get("studentemail", ""),
            "studentaddress": formatted_address,
            "city": city,
            "objective": student_data.get("objective", ""),
            "degreecollege": student_data.get("degreecollege", ""),
            "degreeyearofpass": student_data.get("degreeyearofpass", ""),
            "degreeavgcgpa": student_data.get("degreeavgcgpa", ""),
            "degreeinfo": student_data.get("degreeinfo", []),
            "intercollegename": student_data.get("intercollegename", ""),
            "interboard": student_data.get("interboard", ""),
            "interpercentage": student_data.get("interpercentage", ""),
            "interyearofpass": student_data.get("interyearofpass", ""),
            "sscschoolname": student_data.get("sscschoolname", ""),
            "sscboard": student_data.get("sscboard", ""),
            "sscgpa": student_data.get("sscgpa", ""),
            "sscyearofpass": student_data.get("sscyearofpass", ""),
            "skillset": student_data.get("skillset", []),
            "projectinfo": student_data.get("projectinfo", []),
            "experienceinfo": student_data.get("experienceinfo", []),
            "coursecertification": formatted_certificates,
            "dob": student_data.get("dob", ""),
            "fathername": student_data.get("fathername", ""),
            "fatheroccupation": student_data.get("fatheroccupation", ""),
            "mothername": student_data.get("mothername", ""),
            "motheroccupation": student_data.get("motheroccupation", ""),
            "language":  lang
        }

        page = await app.state.browser.newPage()
        html_content = template.render(student_info=data_for_template)
        pdf_bytes = await generate_pdf(page, html_content)

        base_path = os.path.join(os.getcwd(), drive_name)
        os.makedirs(base_path, exist_ok=True)
        pdf_filename = f"Resume_{safe_student_name}.pdf"
        pdf_path = os.path.join(base_path, pdf_filename)

        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)

        return FileResponse(
            path=pdf_path,
            media_type='application/pdf',
            filename=pdf_filename
        )

    except Exception as e:
        print(f"❌ Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if page is not None:
            await page.close()