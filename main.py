from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
from pymongo import MongoClient
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações do MongoDB de forma local
client = MongoClient("mongodb://localhost:27017")
db = client['nome do banco de dados']
collection = db['nome da collection']

# Função para extrair texto do PDF
def extract_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

#Google Generative AI
genai.configure(api_key='sua chave')  


pdf_content = {}

@app.get("/")
async def root():
    return {"message": "Bem-vindo à API de Análise de Contratos!"}

@app.post("/upload_pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    text = extract_pdf(file.file)
    data = {
        "filename": file.filename,
        "content": text,
    }
    collection.insert_one(data)
    pdf_content[file.filename] = text
    return JSONResponse(content={"message": "PDF processado com sucesso."})

@app.post("/perguntar/")
async def perguntar(filename: str, pergunta: str = Form(...)):
    pdf_data = collection.find_one({"filename": filename})
    if not pdf_data:
        return JSONResponse(content={"error": "PDF não encontrado."}, status_code=400)

    text = pdf_data['content']
    prompt = f"Texto do contrato:\n{text}\n\nPergunta: {pergunta}"

    try:
        response = genai.ChatSession(
            prompt=prompt,
            temperature=0.5,
            max_output_tokens=1000
        )

        ia_response = response['text'] 

        resposta_armazenada = {
            "filename": filename,
            "pergunta": pergunta,
            "ia_response": ia_response
        }
        collection.insert_one(resposta_armazenada)

        return JSONResponse(content={"resposta": ia_response})

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
