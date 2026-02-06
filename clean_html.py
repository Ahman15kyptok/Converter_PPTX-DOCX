import re
from html.parser import HTMLParser
from typing import List, Set

class RestrictedHTMLParser(HTMLParser):
    """Парсер для проверки разрешенных HTML тегов"""
    def __init__(self, allowed_tags: List[str]):
        super().__init__()
        self.allowed_tags = set(allowed_tags)
        self.found_tags: Set[str] = set()
        self.is_valid = True
        self.error_message = ""
    
    def handle_starttag(self, tag: str, attrs: list):
        # Проверяем разрешен ли тег
        if tag not in self.allowed_tags:
            self.is_valid = False
            self.error_message = f"Запрещенный тег: <{tag}>"
            return
        
        self.found_tags.add(tag)
        
        # Проверяем атрибуты на наличие скриптов и стилей
        for attr_name, attr_value in attrs:
            if attr_name.lower() in ['onclick', 'onload', 'onerror', 'style']:
                self.is_valid = False
                self.error_message = f"Запрещенный атрибут: {attr_name}"
                return
            if attr_value and ('javascript:' in attr_value.lower() or 'data:' in attr_value.lower()):
                self.is_valid = False
                self.error_message = f"Запрещенное значение атрибута: {attr_value}"
                return
    
    def handle_endtag(self, tag: str):
        if tag not in self.allowed_tags:
            self.is_valid = False
            self.error_message = f"Запрещенный закрывающий тег: </{tag}>"
    
    def handle_comment(self, data: str):
        self.is_valid = False
        self.error_message = "Комментарии запрещены"
    
    def handle_decl(self, decl: str):
        self.is_valid = False
        self.error_message = "HTML декларации запрещены"
    
    def unknown_decl(self, data: str):
        self.is_valid = False
        self.error_message = "Неизвестные декларации запрещены"

def validate_html(html_content: str, allowed_tags: List[str] = None) -> dict:
    """
    Проверяет валидность HTML и разрешенные теги.
    
    Args:
        html_content: HTML строка для проверки
        allowed_tags: Список разрешенных тегов (по умолчанию: ['div', 'p', 'strong', 'ul', 'li', 'br'])
    
    Returns:
        dict: {
            'is_valid': bool,
            'error_message': str,
            'found_tags': set,
            'allowed_tags': set
        }
    """
    if allowed_tags is None:
        allowed_tags = ['p', 'strong', 'ul', 'li', 'br', 'b', 'strong', 'i']
    
    # Проверяем базовые случаи
    if not html_content or not html_content.strip():
        return {
            'is_valid': False,
            'error_message': 'Пустой HTML контент',
            'found_tags': set(),
            'allowed_tags': set(allowed_tags)
        }
    
    # Проверяем на наличие явно опасных конструкций
    dangerous_patterns = [
        r'<script', r'</script', r'javascript:', r'vbscript:', 
        r'onclick=', r'onload=', r'onerror=', r'style=',
        r'<!--', r'-->', r'<!DOCTYPE', r'<?', r'<%'
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, html_content, re.IGNORECASE):
            return {
                'is_valid': False,
                'error_message': f'Обнаружена опасная конструкция: {pattern}',
                'found_tags': set(),
                'allowed_tags': set(allowed_tags)
            }
    
    # Создаем парсер и проверяем
    parser = RestrictedHTMLParser(allowed_tags)
    
    try:
        parser.feed(html_content)
        parser.close()
        
        # Дополнительная проверка сбалансированности тегов
        if parser.is_valid:
            # Проверяем сбалансированность основных тегов (кроме br)
            balanced_tags = ['div', 'p', 'ul', 'li', 'strong']
            for tag in balanced_tags:
                open_count = html_content.count(f'<{tag}')
                close_count = html_content.count(f'</{tag}')
                if open_count != close_count:
                    parser.is_valid = False
                    parser.error_message = f'Несбалансированные теги <{tag}>: открывающих {open_count}, закрывающих {close_count}'
                    break
        
        return {
            'is_valid': parser.is_valid,
            'error_message': parser.error_message,
            'found_tags': parser.found_tags,
            'allowed_tags': set(allowed_tags)
        }
    
    except Exception as e:
        return {
            'is_valid': False,
            'error_message': f'Ошибка парсинга HTML: {str(e)}',
            'found_tags': set(),
            'allowed_tags': set(allowed_tags)
        }

# Дополнительная функция для санитизации HTML
def sanitize_html(html_content: str, allowed_tags: List[str] = None) -> str:
    """
    Очищает HTML, оставляя только разрешенные теги.
    Удаляет все атрибуты и опасный контент.
    """
    if allowed_tags is None:
        allowed_tags = ['div', 'p', 'strong', 'ul', 'li', 'br']
    
    # Удаляем все атрибуты из тегов
    def remove_attributes(match):
        tag = match.group(1)
        return f'<{tag}>'
    
    # Паттерн для нахождения тегов с атрибутами
    pattern = r'<(\w+)(\s+[^>]*)>'
    clean_html = re.sub(pattern, remove_attributes, html_content)
    
    # Удаляем все запрещенные теги
    allowed_pattern = '|'.join(allowed_tags)
    # Удаляем закрывающие теги для неразрешенных элементов
    clean_html = re.sub(r'</(?!(' + allowed_pattern + r')\b)[^>]+>', '', clean_html)
    # Удаляем открывающие теги для неразрешенных элементов
    clean_html = re.sub(r'<(?!(' + allowed_pattern + r')\b|/?(' + allowed_pattern + r')\b)[^>]+>', '', clean_html)
    
    return clean_html