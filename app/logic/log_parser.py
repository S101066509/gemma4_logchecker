import re

def clean_log_text(text: str) -> str:
    """
    對日誌進行初步清洗與脫敏 (Anonymization)
    """
    # 1. 脫敏：替代 IP 位址 (IPv4/IPv6)
    text = re.sub(r'\b\d{1,3}(?:\.\d{1,3}){3}\b', 'XXX.XXX.XXX.XXX', text)
    text = re.sub(r'\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{1,4}\b', 'XXXX:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX:XXXX', text)
    
    # 2. 脫敏：簡單替換用戶路徑 (針對 Unix 系統)
    text = re.sub(r'/Users/[\w-]+', '/Users/USER', text)
    text = re.sub(r'/home/[\w-]+', '/home/USER', text)

    # 3. 脫敏：Windows 使用者路徑
    text = re.sub(r'[A-Za-z]:\\Users\\[^\\]+', r'C:\\Users\\USER', text)

    # 4. 脫敏：Email
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', 'USER@DOMAIN', text)

    # 5. 脫敏：常見 Token (JWT / 長字串)
    text = re.sub(r'\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\b', 'JWT_TOKEN', text)
    text = re.sub(r'\b[A-Za-z0-9_\-]{32,}\b', 'REDACTED_TOKEN', text)

    # 6. 脫敏：關鍵字後的敏感值 (API key / secret / password 等)
    text = re.sub(
        r'(?i)\b(api[_-]?key|secret|password|token|access[_-]?key)\b\s*[:=]\s*[^\s]+',
        r'\1=REDACTED',
        text
    )
    
    return text

def extract_critical_sections(text: str, window_size: int = 50, max_lines: int = 400) -> str:
    """
    從長日誌中提取關鍵片段 (ERROR, CRITICAL, PANIC 等)
    避免將幾萬行無意義的 INFO 丟給 LLM
    """
    lines = text.splitlines()
    critical_keywords = ["ERROR", "CRITICAL", "PANIC", "FATAL", "EXCEPTION", "FAIL"]
    
    critical_indices = [
        i for i, line in enumerate(lines) 
        if any(kw in line.upper() for kw in critical_keywords)
    ]
    
    if not critical_indices:
        # 如果沒發現關鍵字，則回傳前 200 行作為概覽
        return "\n".join(lines[:200])
    
    # 提取關鍵行前後的上下文
    result_lines = set()
    for idx in critical_indices:
        start = max(0, idx - window_size)
        end = min(len(lines), idx + window_size)
        for i in range(start, end):
            result_lines.add(i)
            
    # 按順序重新組合
    sorted_indices = sorted(list(result_lines))
    
    final_output = []
    last_idx = -1
    for idx in sorted_indices:
        if last_idx != -1 and idx > last_idx + 1:
            final_output.append("... (已省略無關日誌) ...")
        final_output.append(lines[idx])
        last_idx = idx
        
    if len(final_output) > max_lines:
        final_output = final_output[:max_lines]
        final_output.append("... (已省略更多關鍵日誌) ...")

    return "\n".join(final_output)
