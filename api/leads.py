from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import re
from datetime import datetime

# URL do Google Sheets (mantida no backend por segurança)
GOOGLE_SHEETS_URL = "https://script.google.com/macros/s/AKfycbxk5Lir91KwIZ3IRu3J57CmB9UHknyYhdv7gTHApE-jmtT82NPrqCm1wacQFIkZ4pFbEw/exec"


def validate_phone(phone):
    """Valida número de telefone brasileiro."""
    # Remove tudo que não é dígito
    digits = re.sub(r'\D', '', phone)
    # Número brasileiro: 11 dígitos (DDD + 9 dígitos)
    return len(digits) >= 10 and len(digits) <= 11


def save_to_sheets(whatsapp):
    """Salva lead no Google Sheets."""
    try:
        data = json.dumps({"whatsapp": whatsapp}).encode('utf-8')
        req = urllib.request.Request(
            GOOGLE_SHEETS_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return True
    except Exception as e:
        print(f"Error saving to sheets: {e}")
        return False


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Limitar tamanho do request (máx 1KB para leads)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 1024:
            self.send_error_response(400, "Request too large")
            return

        try:
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            whatsapp = data.get('whatsapp', '')

            # Validar telefone
            if not whatsapp or not validate_phone(whatsapp):
                self.send_error_response(400, "Número de WhatsApp inválido")
                return

            # Salvar no Google Sheets
            success = save_to_sheets(whatsapp)

            if success:
                self.send_success_response({"message": "Lead salvo com sucesso"})
            else:
                self.send_error_response(500, "Erro ao salvar lead")

        except json.JSONDecodeError:
            self.send_error_response(400, "JSON inválido")
        except Exception as e:
            print(f"Lead API error: {e}")
            self.send_error_response(500, "Erro interno")

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def send_success_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_error_response(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
