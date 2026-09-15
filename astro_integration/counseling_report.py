import json
import os
import sys
import requests

# Projenin kök dizinini sistem yoluna ekler
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

COUNSELING_PROMPT = """Bir psikolojik astrolog ve yaşam mentörü olarak, aşağıdaki doğum haritası verilerine dayanarak doğrudan danışanla konuşuyormuş gibi bir danışmanlık metni üret.

Yazım biçimi:
- Birincil kişi ağzından konuş (Ben dili kullan).
- Sohbet tonunda ama karizmatik ve güven veren ol.
- Derin ama anlaşılır anlat.
- Teknik astroloji terimlerini kullanma (kare, üçgen, dispozitör vs. söyleme).
- Teknik analiz arka planda çalışsın ama çıktı tamamen hayat diliyle olsun.
- Deneyimli bir astrolog etkisi ver.
- Danışanı hem rahatlat hem de gerektiğinde sars.
- Gereksiz spiritüel süslemeler yapma; psikolojik ve gerçekçi ol.

Konuşma şu akışta ilerlesin:

1) Güçlü bir açılış yap.
Danışanın hayat temasını tek cümlelik çarpıcı bir manifesto ile başlat.
Blockquote formatında yaz:
> "SEN ..."
İlk 2 paragrafta danışan kendini net görülmüş hissetsin.

2) Enerji akışını anlat.
Hayatındaki alanların nasıl birbirini beslediğini sebep-sonuç ilişkisiyle açıkla.
Modern dünya bağlamı ekle (kariyer baskısı, sosyal medya, görünürlük, yalnızlık vs.).
Soyut + somut metafor birlikte kullan:
- paslanmış anahtar
- freni zayıf araba
- kilitli oda
- yarım kalmış inşaat
- motoru güçlü ama direksiyonu hassas araç

3) Karmik yönü anlat.
Konfor alanını ve gitmesi gereken yönü açıkça söyle.
Eski kimliği tanımla.
Yeni kimliğin nasıl biri olduğunu tarif et.
Bir eşik cümlesi koy:
> "Hayat seni bir noktada seçim yapmaya zorlayacak."

4) Şifa alanını anlat.
En hassas olduğu noktayı söyle.
Bunu zayıflık değil güç potansiyeli olarak çerçevele.
"Yaran başkasının ilacı olabilir." benzeri bir cümle kullan ama klişe kaçma.

5) YÜZLEŞME VAKTİ başlığı aç.
Bu bölümü net ve cesur yaz.
Blockquote ile giriş yap:
> "Şimdi sana dürüst olacağım."
Kendini sabote ettiği davranışları açıkça yaz:
- erteleme
- aşırı kontrol
- fazla hırs
- duygusal geri çekilme
- onay bağımlılığı
Yumuşatma yapma ama suçlama da yapma.
Net bir cümle ile bitir:
***"Potansiyelini ya sen yöneteceksin ya da gölgen yönetecek."***

6) İlişki senaryosu oluştur.
Partner veya iş ortamında tipik bir çatışma diyaloğu yaz:
- "Ben sadece biraz alan istiyorum."
- "Ama sen uzaklaşıyorsun gibi hissediyorum."
Bu çatışmanın psikolojik kökünü açıkla.
Sonra danışana kullanabileceği bir cümle öner.

7) 3 maddelik net eylem planı ver.
Soyut değil, uygulanabilir olsun.
Ölçülebilir mikro aksiyonlar yaz.

8) Güçlü kapanış yap.
Son cümle karizmatik, net ve güven veren olsun.
Haritanın kader değil bilinç potansiyeli olduğunu vurgula.

Dil:
- Bilgece
- Net
- Güven veren
- Fazla uzun değil ama derin
- Gereksiz kelime kalabalığı yok
- Kritik cümleleri blockquote veya yıldızlı vurguyla belirt

Amaç:
Danışan hem rahatlasın hem düşünmeye başlasın.
Hem anlaşılmış hissetsin hem de sorumluluk alsın.
Metin doğal bir danışmanlık konuşması gibi aksın.
"""


def generate_counseling_report():
    # 1. test_output.json'u oku
    # Bu dosya counseling_report.py ile aynı dizinde olmalı (astro_integration/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "test_output.json")

    if not os.path.exists(output_path):
        print("Hata: test_output.json bulunamadı!")
        print(f"Beklenen konum: {output_path}")
        return

    with open(output_path, "r", encoding="utf-8") as f:
        chart_data = json.load(f)

    # 2. API Key - .env'den veya buraya direkt yaz
    API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCH97_3JkEv2dEz-DmnCUQ3qKAk0CD9i2E")

    # 3. Harita verisini prompt'a ekle
    chart_json_str = json.dumps(chart_data, ensure_ascii=False, indent=2)
    full_prompt = f"{COUNSELING_PROMPT}\n\nDANIŞAN'IN DOĞUM HARİTASI VERİSİ:\n{chart_json_str}"

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 12000,
            "topP": 0.95,
            "candidateCount": 1
        }
    }

    headers = {"Content-Type": "application/json"}

    print("🧠 Psikolojik danışmanlık raporu hazırlanıyor, lütfen bekleyin...")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)

        if response.status_code != 200:
            print(f"Hata: {response.status_code} - {response.text}")
            return

        result = response.json()

        if "candidates" in result and result["candidates"]:
            report = result["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print("API yanıtında içerik bulunamadı.")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return

        print("\n" + "=" * 60)
        print("PSİKOLOJİK DANIŞMANLIK RAPORU")
        print("=" * 60 + "\n")
        print(report)

        # Raporu dosyaya da kaydet
        report_path = os.path.join(script_dir, "counseling_output.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"\n✅ Rapor kaydedildi: {report_path}")

    except requests.exceptions.RequestException as e:
        print(f"Bağlantı hatası: {str(e)}")


if __name__ == "__main__":
    generate_counseling_report()