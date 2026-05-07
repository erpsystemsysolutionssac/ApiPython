from pydantic import BaseModel

class PostDataSunat(BaseModel):
    ruc_sol: str
    usuario_sol: str
    clave_sol: str
    client_id: str
    client_secret: str
    ruc_proveedor: str 
    serie: str 
    numero: str