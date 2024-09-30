from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
from pymongo import MongoClient
import google.generativeai as genai

# Inicializa o FastAPI
app = FastAPI()

# Middleware para permitir CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos os origens
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações do MongoDB
client = MongoClient("mongodb://localhost:27017")
db = client['Guba']
collection = db['respostas']

# Função para extrair texto do PDF
def extract_pdf(file):
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text()
    return text

# Configurações do Google Generative AI
genai.configure(api_key='YOUR_API_KEY')  # Coloque sua chave de API aqui

# Variável para armazenar o conteúdo do PDF processado
pdf_content = {}

# Endpoint raiz
@app.get("/")
async def root():
    return {"message": "Bem-vindo à API de Análise de Contratos!"}

# 1. Endpoint para upload do PDF e processamento pela IA
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

# 2. Endpoint para o usuário enviar uma pergunta sobre o PDF já processado
@app.post("/perguntar/")
async def perguntar(filename: str, pergunta: str = Form(...)):
    pdf_data = collection.find_one({"filename": filename})
    if not pdf_data:
        return JSONResponse(content={"error": "PDF não encontrado."}, status_code=400)

    text = pdf_data['content']
    prompt = f"Texto do contrato:\n{text}\n\nPergunta: {pergunta}"

    try:
        response = genai.generate_text(
            prompt=prompt,
            temperature=0.5,
            max_output_tokens=1000
        )

        ia_response = response['text']  # Ajuste de acordo com a resposta retornada

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
