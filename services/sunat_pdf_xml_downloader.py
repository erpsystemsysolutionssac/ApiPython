from playwright.sync_api import Page, sync_playwright
from typing import Callable, Any

class SunatPdfDownloader:
    """
    Servicio encargado de interactuar con el portal SOL de SUNAT para
    descargar los comprobantes (PDF) y sus archivos XML asociados.
    """

    def _init_browser_session(self, p: Any) -> tuple[Any, Any, Page]:
        """Inicia la sesión de navegador con configuración anti-detección."""
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--start-maximized', 
                '--no-sandbox'
            ]
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Script para ocultar propiedades de automatización
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        return browser, context, page
    
    def _login(self, page: Page, ruc_sol: str, usuario_sol: str, clave_sol: str, callback_status: Callable) -> None:
        """Realiza el login en SUNAT SOL."""
        callback_status("Accediendo al login de SUNAT...")
        page.goto("https://api-seguridad.sunat.gob.pe/v1/clientessol/4f3b88b3-d9d6-402a-b85d-6a0bc857746a/oauth2/loginMenuSol?lang=es-PE&showDni=true&showLanguages=false&originalUrl=https://e-menu.sunat.gob.pe/cl-ti-itmenu/AutenticaMenuInternet.htm&state=rO0ABXNyABFqYXZhLnV0aWwuSGFzaE1hcAUH2sHDFmDRAwACRgAKbG9hZEZhY3RvckkACXRocmVzaG9sZHhwP0AAAAAAAAx3CAAAABAAAAADdAADZXhlcHQABnBhcmFtc3QASyomKiYvY2wtdGktaXRtZW51L01lbnVJbnRlcm5ldC5odG0mYjY0ZDI2YThiNWFmMDkxOTIzYjIzYjY0MDdhMWMxZGI0MWU3MzNhNnQABGV4ZWNweA==")
        
        page.fill("#txtRuc", ruc_sol)
        page.fill("#txtUsuario", usuario_sol)
        page.fill("#txtContrasena", clave_sol)
        page.click("#btnAceptar")

    def _get_tipo_label(self, tipo_doc: str, serie: str) -> str:
        """
        Retorna la palabra clave de búsqueda para filtrar el dropdown
        del portal SUNAT (Consulta de Comprobantes de Pago).
        Dinamismo extra para distinguir "Factura" vs "Boleta" en Notas de Crédito y Débito
        en base a la regla: las Boletas y sus notas inician con 'B'.
        """
        # Limpiar cualquier cosa como '7' o '7.0' -> '07'
        tipo = str(tipo_doc).strip().replace(".0", "")
        if tipo.isdigit():
            tipo = tipo.zfill(2)

        s_upper = str(serie).strip().upper()
        
        if tipo == "01":
            return "Factura"
        elif tipo == "03":
            return "Boleta de venta"
        elif tipo == "07":
            if s_upper.startswith("B"):
                return "Boleta de Venta - Nota de Crédito"
            elif s_upper.startswith("T"):
                return "Ticket POS - Nota de Crédito"
            else:
                return "Factura - Nota de Crédito"
        elif tipo == "08":
            if s_upper.startswith("B"):
                return "Boleta de Venta - Nota de Débito"
            elif s_upper.startswith("T"):
                return "Ticket POS - Nota de Débito"
            else:
                return "Factura - Nota de Débito"
        
        return "Factura"

    def download_pdf(self, ruc_sol: str, usuario_sol: str, clave_sol: str,  ruc_emisor: str, serie: str, numero: str, callback_status: Callable, tipo_doc: str = "01") -> str:
        """
        Descarga el PDF y el XML del comprobante usando Playwright.
        Soporta Facturas (01), Boletas (03), Notas de Crédito (07) y Notas de Débito (08).
        Retorna la ruta del PDF descargado.
        """
        print("Iniciando Tipo Label")
        tipo_label = self._get_tipo_label(tipo_doc, serie)
        print(tipo_label)
        callback_status(f"Iniciando descarga de PDF y XML {serie}-{numero} [{tipo_label}] de {ruc_emisor}...")
        
        # Preparar directorios
        # base_dir = os.getcwd()
        # pdf_dir = get_file_path(base_dir, os.path.join('downloads', 'pdf'))
        # xml_dir = get_file_path(base_dir, os.path.join('downloads', 'xml'))
        # zip_dir = get_file_path(base_dir, os.path.join('downloads', 'zip'))
        
        # ensure_directory_exists(pdf_dir)
        # ensure_directory_exists(xml_dir)
        # ensure_directory_exists(zip_dir)

        # nombre_base = f"{serie}-{numero}"
        # target_pdf_path = get_file_path(pdf_dir, f"{nombre_base}.pdf")
        # target_zip_path = get_file_path(zip_dir, f"{nombre_base}.zip")

        with sync_playwright() as p:
            browser, context, page = self._init_browser_session(p)
            try:
                self._login(page, ruc_sol, usuario_sol, clave_sol, callback_status)
                # self._handle_popups(page)
                # self._navigate_to_voucher_lookup(page, callback_status)
                # Pasar tipo_label para selección dinámica en el formulario
                # app_frame = self._fill_consultation_form(page, ruc_emisor, serie, numero, callback_status, tipo_label)
                # self._perform_file_downloads(page, app_frame, target_pdf_path, target_zip_path, callback_status)

                # Extraer descripción si se descargó el XML
                # if os.path.exists(target_zip_path):
                #      self._extract_description_from_zip(target_zip_path, xml_dir, nombre_base)
                
                callback_status(f"✓ ¡ÉXITO! Proceso completado.")
                return "target_pdf_path"

            except Exception as e:
                callback_status(f"Error descargando archivos: {e}")
                raise e
            finally:
                browser.close()