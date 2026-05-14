from playwright.sync_api import Page, sync_playwright
import time
import os
import zipfile
import base64
import shutil
from typing import Callable, Any

from utils.file_utils import ensure_directory_exists, get_file_path

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
                '--no-sandbox',
                "--disable-dev-shm-usage"
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

    def _handle_popups(self, page: Page) -> None:
        """Maneja los modales de campaña o publicidad inicial."""
        print("Esperando modales de campaña...")
        try:
            iframe_campana = page.frame_locator("#ifrVCE")
            
            # Click en Finalizar
            btn_finalizar = iframe_campana.get_by_role("button", name="Finalizar")
            btn_finalizar.wait_for(state="visible", timeout=10000)
            btn_finalizar.click()
            print("✓ Modal 'Finalizar' cerrado.")

            # Click en Finalizar
            btn_finalizar = iframe_campana.get_by_role("button", name="Finalizar")
            btn_finalizar.wait_for(state="visible", timeout=10000)
            btn_finalizar.click()
            print("✓ Modal 'Finalizar' cerrado.")

            # Click en Continuar sin confirmar
            btn_continuar = iframe_campana.get_by_text("Continuar sin confirmar")
            btn_continuar.wait_for(state="visible", timeout=5000)
            btn_continuar.click()
            print("✓ Pantalla de validación saltada.")
            
            time.sleep(2) 
        except Exception:
            print("- No se detectó el modal o tardó demasiado. Continuando...")

    def _navigate_to_voucher_lookup(self, page: Page, callback_status: Callable) -> None:
        """Navega a través del menú hasta la opción de Consulta de Comprobantes."""
        callback_status("Navegando al menú de Comprobantes...")
        try:
            page.locator(".list-group-item").filter(has_text="Empresas").first.click(force=True)
            time.sleep(1.5)

            def navegar_lista(texto: str) -> None:
                item = page.get_by_text(texto, exact=True).first
                item.wait_for(state="visible", timeout=10000)
                item.click(force=True)
                time.sleep(0.8)

            navegar_lista("Comprobantes de pago")
            navegar_lista("Comprobantes de Pago")
            navegar_lista("Consulta de Comprobantes de Pago")
            
            link_final = page.get_by_text("Nueva Consulta de comprobantes de pago", exact=True).first
            link_final.wait_for(state="visible", timeout=10000)
            link_final.click(force=True)
            callback_status("✓ Ruta de navegación completada.")

        except Exception as e:
            callback_status(f"Fallo en navegación del menú: {e}")
            raise e
        
    def _fill_consultation_form(self, page: Page, ruc_emisor: str, serie: str, numero: str, callback_status: Callable, tipo_label: str = "Factura") -> Any:
        """Llena el formulario de consulta de comprobantes."""
        callback_status("Buscando formulario...")
        app_frame = page.frame_locator("#iframeApplication")
        
        try:
            page.wait_for_selector("ngx-spinner", state="hidden", timeout=15000)
            
            radio_recibido = app_frame.get_by_text("Recibido", exact=True)
            radio_recibido.wait_for(state="visible", timeout=15000)
            radio_recibido.click()
            callback_status("✓ Cambio a 'Recibido' realizado.")
            time.sleep(2)

            # Re-confirmar 'Recibido'
            try:
                app_frame.get_by_text("Recibido", exact=True).click()
            except:
                pass
            time.sleep(2)

            txt_ruc = app_frame.locator("#rucEmisor, [formcontrolname='rucEmisor']").first
            txt_ruc.fill(ruc_emisor)
            callback_status(f"✓ RUC {ruc_emisor} ingresado.")

            # Selector de Tipo (PrimeNG) — dinámico según tipo de comprobante
            dropdown_tipo = app_frame.locator("p-dropdown[formcontrolname='tipoComprobanteI']")
            dropdown_tipo.wait_for(state="visible", timeout=10000)
            dropdown_tipo.click()
            
            buscador_interno = app_frame.locator("input.p-dropdown-filter")
            buscador_interno.wait_for(state="visible", timeout=5000)
            buscador_interno.fill(tipo_label)
            
            time.sleep(1.5)
            
            # exact=True es crítico: evita seleccionar "Factura - Nota de Crédito"
            # cuando se busca "Factura", ya que ambas contienen esa palabra.
            opcion = app_frame.get_by_role("option", name=tipo_label, exact=True)
            opcion.wait_for(state="visible", timeout=5000)
            opcion.click()
            callback_status(f"✓ '{tipo_label}' seleccionado.")
            
            # Serie y Número
            app_frame.locator("input[formcontrolname='serieComprobante'], #serie").first.fill(serie)
            app_frame.locator("input[formcontrolname='numeroComprobante'], #numero").first.fill(numero)
            
            callback_status("Consultando...")
            app_frame.get_by_role("button", name="Consultar").click()
            
            return app_frame

        except Exception as e:
            callback_status(f"⚠️ Error en interacción con formulario: {e}")
            raise e
        
    def _perform_file_downloads( self, page: Page, app_frame: Any, target_pdf_path: str, target_zip_path: str, callback_status: Callable) -> dict[str, Any]:
        """
        Ejecuta la descarga del PDF y XML.

        Retorna:
        {
            "success": bool,
            "message": str,
            "pdf_downloaded": bool,
            "xml_downloaded": bool,
            "pdf_path": str | None,
            "zip_path": str | None
        }
        """
        result = {
            "success": False,
            "message": "",
            "pdf_downloaded": False,
            "xml_downloaded": False,
            "pdf_path": None,
            "zip_path": None
        }

        callback_status("Esperando resultado de búsqueda...")

        # =========================================================
        # ESPERAR RESPUESTA DE SUNAT
        # =========================================================
        try:
            app_frame.get_by_text( "Resultado", exact=False).wait_for( state="visible", timeout=15000 )
        except Exception:
            # Validar si SUNAT respondió "No hay resultados"
            try:
                no_resultado = app_frame.get_by_text( "No hay resultados", exact=False )

                if no_resultado.is_visible(timeout=1000):

                    mensaje = ( "La SUNAT indica que no hay resultados para la consulta.")
                    callback_status(mensaje)
                    result["message"] = mensaje

                    return result

            except Exception as ex_no_result:

                callback_status(f"Error verificando mensaje SUNAT: {str(ex_no_result)}")

            mensaje = "Timeout esperando respuesta de SUNAT."
            callback_status(mensaje)
            result["message"] = mensaje

            return result

        # =========================================================
        # DESCARGAR PDF
        # =========================================================
        try:
            btn_pdf = app_frame.locator("button[ngbtooltip='Descargar PDF']").first
            btn_pdf.wait_for( state="visible", timeout=10000)
            callback_status("✓ Botón PDF detectado. Descargando PDF...")

            with page.expect_download(timeout=30000) as download_info:

                btn_pdf.click()

            download = download_info.value
            download.save_as(target_pdf_path)

            # Validar existencia
            if not os.path.exists(target_pdf_path):

                mensaje = "El PDF no fue descargado correctamente."
                callback_status(mensaje)
                result["message"] = mensaje
                return result

            # Validar tamaño
            if os.path.getsize(target_pdf_path) == 0:

                mensaje = "El PDF descargado está vacío."
                callback_status(mensaje)
                result["message"] = mensaje

                return result

            result["pdf_downloaded"] = True
            result["pdf_path"] = target_pdf_path

            callback_status("✓ PDF descargado correctamente.")
        except Exception as ex_pdf:
            mensaje = f"Error descargando PDF: {str(ex_pdf)}"
            callback_status(mensaje)
            result["message"] = mensaje

            return result

        # Espera pequeña para evitar conflictos SUNAT
        page.wait_for_timeout(1000)

        # =========================================================
        # DESCARGAR XML
        # =========================================================
        try:
            btn_xml = app_frame.locator("button[ngbtooltip='Descargar XML']").first
            # Validar existencia real
            if btn_xml.count() > 0:
                callback_status("Descargando XML...")

                with page.expect_download(timeout=30000) as download_info_xml:

                    btn_xml.click()

                download_xml = download_info_xml.value
                download_xml.save_as(target_zip_path)

                # Validar existencia
                if os.path.exists(target_zip_path):

                    # Validar tamaño
                    if os.path.getsize(target_zip_path) > 0:
                        result["xml_downloaded"] = True
                        result["zip_path"] = target_zip_path
                        callback_status("✓ XML descargado correctamente.")
                    else:
                        callback_status("⚠️ XML descargado pero vacío.")
                else:
                    callback_status("⚠️ XML no fue descargado correctamente.")
            else:
                callback_status("⚠️ Botón XML no disponible.")
        except Exception as ex_xml:
            callback_status(f"⚠️ Error descargando XML: {str(ex_xml)}")

        # =========================================================
        # RESULTADO FINAL
        # =========================================================
        result["success"] = True
        if result["xml_downloaded"]:
            result["message"] = ("PDF y XML descargados correctamente.")
        else:
            result["message"] = ("PDF descargado correctamente.")

        return result

    def _extract_files_from_zip( self, zip_path: str, xml_dir: str, cdr_dir: str, callback_status) -> dict[str, Any]:

        result = {
            "success": False,
            "xml_path": None,
            "cdr_path": None,
            "message": ""
        }

        try:

            if not os.path.exists(zip_path):
                result["message"] = "ZIP no encontrado."
                return result

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:

                file_list = zip_ref.namelist()

                if not file_list:
                    result["message"] = "ZIP vacío."
                    return result

                callback_status(f"Archivos encontrados en ZIP: {len(file_list)}")

                for file_name in file_list:

                    lower_name = file_name.lower()

                    # =====================================================
                    # XML DEL COMPROBANTE
                    # =====================================================
                    if lower_name.endswith(".xml") and not lower_name.startswith("r-"):

                        target_xml_path = os.path.join( xml_dir, os.path.basename(file_name))

                        with zip_ref.open(file_name) as source_file:
                            with open(target_xml_path, "wb") as target_file:
                                target_file.write(source_file.read())

                        result["xml_path"] = target_xml_path
                        callback_status(f"✓ XML extraído: {os.path.basename(file_name)}")

                    # =====================================================
                    # CDR
                    # =====================================================
                    elif lower_name.startswith("r-") and lower_name.endswith(".xml"):

                        target_cdr_path = os.path.join(cdr_dir,os.path.basename(file_name))

                        with zip_ref.open(file_name) as source_file:
                            with open(target_cdr_path, "wb") as target_file:
                                target_file.write(source_file.read())

                        result["cdr_path"] = target_cdr_path
                        callback_status(f"✓ CDR extraído: {os.path.basename(file_name)}")

            result["success"] = True
            result["message"] = "Archivos extraídos correctamente."
            return result

        except zipfile.BadZipFile:
            result["message"] = "El archivo ZIP está corrupto."
            return result

        except Exception as ex:
            result["message"] = f"Error extrayendo ZIP: {str(ex)}"
            return result

    def file_to_base64_response(self, file_path: str, mime_type: str):
        if not os.path.exists(file_path):
            return None

        with open(file_path, "rb") as file:
            encoded = base64.b64encode(file.read()).decode("utf-8")

        return {
            "filename": os.path.basename(file_path),
            "mime_type": mime_type,
            "base64": encoded
        }

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
        base_dir = os.getcwd()
        pdf_dir = get_file_path(base_dir, os.path.join('downloads', 'pdf', ruc_sol))
        xml_dir = get_file_path(base_dir, os.path.join('downloads', 'xml', ruc_sol))
        cdr_dir = get_file_path(base_dir, os.path.join('downloads', 'cdr', ruc_sol))
        zip_dir = get_file_path(base_dir, os.path.join('downloads', 'zip', ruc_sol))
        
        ensure_directory_exists(pdf_dir)
        ensure_directory_exists(xml_dir)
        ensure_directory_exists(cdr_dir)
        ensure_directory_exists(zip_dir)

        nombre_base = f"{ruc_emisor}-{tipo_doc}-{serie}-{numero}"
        target_pdf_path = get_file_path(pdf_dir, f"{nombre_base}.pdf")
        target_zip_path = get_file_path(zip_dir, f"{nombre_base}.zip")

        target_xml_path = get_file_path(xml_dir, f"{nombre_base}.xml")
        target_cdr_path = get_file_path(cdr_dir, f"R-{nombre_base}.xml")

        with sync_playwright() as p:
            browser, context, page = self._init_browser_session(p)
            try:
                self._login(page, ruc_sol, usuario_sol, clave_sol, callback_status)
                self._handle_popups(page)
                self._navigate_to_voucher_lookup(page, callback_status)
                # Pasar tipo_label para selección dinámica en el formulario
                app_frame = self._fill_consultation_form(page, ruc_emisor, serie, numero, callback_status, tipo_label)
                resultado_descarga = self._perform_file_downloads(page, app_frame, target_pdf_path, target_zip_path, callback_status)

                if not resultado_descarga["success"]:
                    return resultado_descarga
                # Extraer descripción si se descargó el XML
                if os.path.exists(target_zip_path):
                    resultado_extract  = self._extract_files_from_zip(target_zip_path, xml_dir, cdr_dir, callback_status)

                # Buscar XML y CDR extraídos
                xml_file = None
                cdr_file = None

                for file in os.listdir(xml_dir):
                    if file.lower().endswith(".xml"):
                        archivo_original = os.path.join(xml_dir, file)
                        # Copiar con nombre estándar
                        shutil.copy2(archivo_original, target_xml_path)
                        xml_file = target_xml_path
                        break

                for file in os.listdir(cdr_dir):
                    if file.lower().endswith(".xml"):
                        archivo_original = os.path.join(cdr_dir, file)
                        # Copiar con nombre estándar
                        shutil.copy2(archivo_original, target_cdr_path)
                        cdr_file = target_cdr_path
                        break
                
                callback_status(f"✓ ¡ÉXITO! Proceso completado.")
                response_data = {
                    "success": True,

                    "pdf_path": self.file_to_base64_response(
                        target_pdf_path,
                        "application/pdf"
                    ),

                    "xml": self.file_to_base64_response(
                        xml_file,
                        "application/xml"
                    ) if xml_file else None,

                    "cdr": self.file_to_base64_response(
                        cdr_file,
                        "application/xml"
                    ) if cdr_file else None
                }

                archivos_eliminar = [
                    target_pdf_path,
                    target_zip_path,
                    xml_file,
                    cdr_file
                ]

                for archivo in archivos_eliminar:
                    try:
                        if archivo and os.path.exists(archivo):
                            os.remove(archivo)
                    except Exception as e:
                        print(f"Error eliminando archivo {archivo}: {e}")

                callback_status("✓ ¡ÉXITO! Proceso completado.")

                return response_data

                
                return {
                    "success": True,
                    "pdf_path": self.file_to_base64_response(
                        target_pdf_path,
                        "application/pdf"
                    ),

                    "xml": self.file_to_base64_response(
                        xml_file,
                        "application/xml"
                    ) if xml_file else None,

                    "cdr": self.file_to_base64_response(
                        cdr_file,
                        "application/xml"
                    ) if cdr_file else None
                }

            except Exception as e:
                # # callback_status(f"Error descargando archivos: {e}")
                # # raise e
                error_message = str(e)
                callback_status(f"Error descargando archivos: {error_message}")

                return {
                    "success": False,
                    "message": error_message,
                    "pdf_path": None,
                    "zip_path": None
                }
            finally:
                browser.close()