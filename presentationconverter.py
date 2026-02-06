import os
import mimetypes
import requests
from dotenv import load_dotenv
import aiohttp
import asyncio

load_dotenv()

class PresentationConverter:

    SUPPORTED_EXTENSIONS = {'ppt', 'pptx', 'odp'}

    def __init__(self):
        gotenberg_url = os.getenv("GOTENBERG_URL")
        if not gotenberg_url:
            raise ValueError("Переменная GOTENBERG_URL не задана в .env файле")
        
        self.gotenberg_url = gotenberg_url.rstrip('/') + '/forms/libreoffice/convert'


    def is_presentation(self, file_path: str) -> bool:
        """
        Проверяет, является ли файл поддерживаемой презентацией.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.SUPPORTED_EXTENSIONS


    def is_pdf(self, file_path: str) -> bool:
        """
        Проверяет, является ли файл PDF.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type == 'application/pdf'

    def is_presentation_memory(self, file_extension: str) -> bool:
        """Проверяет, является ли файл поддерживаемой презентацией"""
        return file_extension in self.SUPPORTED_EXTENSIONS

    def is_pdf_memory(self, filename: str) -> bool:
        """Проверяет, является ли файл PDF"""
        return filename.lower().endswith('.pdf')

    def convert_to_pdf(self, file_path: str, output_path: str = None) -> str:
        """
        Отправляет файл в Gotenberg на конвертацию в PDF.
        Возвращает путь к сохранённому PDF-файлу.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
        
        if not self.is_presentation(file_path):
            raise ValueError(f"Файл {file_path} не является поддерживаемой презентацией "
                             f"({', '.join(self.SUPPORTED_EXTENSIONS)})")

        with open(file_path, 'rb') as f:
            files = {
                'files': (os.path.basename(file_path), f, 'application/octet-stream')
            }
            response = requests.post(self.gotenberg_url, files=files)

        if response.status_code != 200:
            raise Exception(f"Gotenberg вернул ошибку: {response.status_code} — {response.text}")

        # Сохраняем PDF-файл
        if output_path is None:
            base, _ = os.path.splitext(file_path)
            output_path = base + '.pdf'

        with open(output_path, 'wb') as out_file:
            out_file.write(response.content)

        return output_path

    async def convert_to_pdf_in_memory(
        self,
        file_content: bytes,
        filename: str,
        session: aiohttp.ClientSession,
        attempt: int = 0
    ) -> bytes:
        """Конвертирует файл в PDF в памяти без сохранения на диск"""
        await asyncio.sleep(3)

        form = aiohttp.FormData()
        form.add_field('files', file_content, filename=filename, content_type='application/octet-stream')

        async with session.post(self.gotenberg_url, data=form) as response:
            if response.status != 200:
                error_text = await response.text()
                if attempt >= 2:
                    raise Exception(f"Gotenberg вернул ошибку: {response.status} — {error_text}")
                else:
                    return await self.convert_to_pdf_in_memory(file_content, filename, session, attempt + 1)

            pdf_content = await response.read()
            return pdf_content


#converter = PresentationConverter()

#file_path = "/mnt/c/Users/user/Desktop/StartStage/AI/check_slide/test/t1.pdf"

#if converter.is_pdf(file_path):
#    print("Это PDF.")
#else:
#    pdf_path = converter.convert_to_pdf(file_path)
#    print(f"Файл успешно конвертирован: {pdf_path}")
