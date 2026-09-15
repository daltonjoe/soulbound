# ✦ SoulBound Astro ✦

Doğum haritası hesaplama ve yapay zeka destekli astroloji raporu uygulaması.

**Özellikler:**
- 7 dil desteği (Türkçe, İngilizce, Arapça, Almanca, İspanyolca, Fransızca, Portekizce)
- Swiss Ephemeris ile hassas gezegen hesaplamaları
- AI destekli kişisel astroloji raporları (Google Gemini)
- Tam otomatik şehir / saat dilimi çözümleme
- PWA desteği - iOS ve Android'de ana ekrana ekleyip uygulama gibi kullanma
- Redis cache ile hızlı tekrar sorgular
- Tamamen ücretsiz deploy edilebilir (Render + Hugging Face Static)

**Yerel Geliştirme:**
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```
Ardından tarayıcıyla `http://localhost:8000` adresini aç.

**Kullanım:**
- Web arayüzü için ana sayfayı ziyaret edin
- API dokümantasyonu: `/docs` (Swagger UI)
- Sağlık kontrolü: `/health`

**Powered by:** FastAPI · Swiss Ephemeris · Google Gemini · Render · Hugging Face Static Spaces
