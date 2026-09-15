import json
import os
from core.interpreter import AstroInterpreter

import sys

# Projenin kök dizinini (SoulBound) sistem yoluna ekler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Şimdi import hatasız çalışacaktır
from astro_integration.core.interpreter import AstroInterpreter
# ... geri kalan kodlar

def test_full_flow():
    # 1. Engine çıktısını oku (Az önce ürettiğin dosya)
    output_path = "test_output.json"
    if not os.path.exists(output_path):
        print("Hata: test_output.json bulunamadı! Önce test_engine.py çalıştırılmalı.")
        return

    with open(output_path, "r", encoding="utf-8") as f:
        chart_data = json.load(f)

    # 2. API Key (Buraya kendi key'ini yapıştır veya .env'den çek)
    API_KEY = "AIzaSyCH97_3JkEv2dEz-DmnCUQ3qKAk0CD9i2E" 
    
    # 3. Interpreter'ı başlat ve yorum al
    print("🔮 Harita yorumlanıyor, lütfen bekleyin...")
    interpreter = AstroInterpreter(API_KEY)
    report = interpreter.generate_report(chart_data)

    print("\n" + "="*50)
    print("ASTROLOJİK ANALİZ RAPORU")
    print("="*50 + "\n")
    print(report)

if __name__ == "__main__":
    test_full_flow()