from fastapi import APIRouter
from schemas.post_data_sunat import PostDataSunat

from services.sunat_pdf_xml_downloader import SunatPdfDownloader

sunat = APIRouter()

@sunat.get("/")
def helloworld():
    return "hello world....."

@sunat.post("/api/descargar_sunat_pdf_xml")
def descargar_pdf_xml(postDataSunat: PostDataSunat):
    print(postDataSunat)
    def update_log(msg: str) -> None:
                print(msg)

    print('Iniciando')
    downloader = SunatPdfDownloader()
    result = downloader.download_pdf(postDataSunat.ruc_sol, postDataSunat.usuario_sol, postDataSunat.clave_sol, postDataSunat.ruc_proveedor, postDataSunat.serie, postDataSunat.numero, update_log, tipo_doc = "01")
            
    print(f"✅ Descarga completada: {result}")
    return result