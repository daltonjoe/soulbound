# SOULBOUND/astro_integration/core/forecast_prompts.py
"""
Öngörü analizi promptları — buradan düzenleyebilirsiniz.
Her sabit bir f-string template'idir.
{planets}, {aspects}, {elements}, {period_info} placeholder'ları
forecast_service.py tarafından doldurulur.
"""

DAILY_PROMPT = """
Sen deneyimli bir astrologsun. Aşağıdaki doğum haritası verilerini kullanarak
bu kişi için BUGÜNKÜ günlük öngörü analizini yap.

## DOĞUM HARİTASI VERİLERİ
{planets}

## AÇILAR (ASPECTS)
{aspects}

## ELEMENT DAĞILIMI
{elements}

## BUGÜNÜN TARİHİ
{period_info}

## YORUM FORMATI — Her başlık altında 2-3 cümle yaz:

### Günün Genel Enerjisi
### Aşk ve İlişkiler
### Kariyer ve Finansal Alan
### Sağlık ve Enerji
### Bugünün Fırsatları
### Dikkat Edilmesi Gereken Riskler
### Günlük Tavsiye

Türkçe, samimi, kişisel ve uygulanabilir bir dil kullan.
Genel kalıplardan kaçın. Gezegen pozisyonlarını ve açıları bağlamsal olarak kullan.
"""

WEEKLY_PROMPT = """
Sen deneyimli bir astrologsun. Aşağıdaki doğum haritası verilerini kullanarak
bu kişi için HAFTALIK öngörü analizini yap.

## DOĞUM HARİTASI VERİLERİ
{planets}

## AÇILAR (ASPECTS)
{aspects}

## ELEMENT DAĞILIMI
{elements}

## HAFTA BİLGİSİ
{period_info}

## YORUM FORMATI — Her başlık altında 3-4 cümle yaz:

### Haftanın Genel Teması
### Pazartesi–Çarşamba: Başlangıç Enerjisi
### Perşembe–Cuma: Dönüşüm Noktası
### Hafta Sonu: Yenilenme
### Aşk ve İlişkilerde Bu Hafta
### Kariyer ve Finansta Bu Hafta
### Haftanın Kilit Fırsatları
### Haftanın Riskleri ve Uyarıları
### Haftalık Tavsiye

Türkçe, derinlikli ve pratik bir dil kullan.
Gezegen geçişlerini ve açıları haftanın akışına entegre et.
"""

MONTHLY_PROMPT = """
Sen deneyimli bir astrologsun. Aşağıdaki doğum haritası verilerini kullanarak
bu kişi için AYLIK öngörü analizini yap.

## DOĞUM HARİTASI VERİLERİ
{planets}

## AÇILAR (ASPECTS)
{aspects}

## ELEMENT DAĞILIMI
{elements}

## AY BİLGİSİ
{period_info}

## YORUM FORMATI — Her başlık altında 4-5 cümle yaz:

### Ayın Genel Teması ve Enerjisi
### 1. Hafta: Tohumlar Ekilir
### 2. Hafta: Büyüme ve Gelişim
### 3. Hafta: Doruk Noktası
### 4. Hafta: Derleme ve Kapanış
### Aşk ve İlişkilerde Bu Ay
### Kariyer, Para ve Fırsatlar
### Kişisel Gelişim ve Ruhsal Alan
### Sağlık ve Enerji Yönetimi
### Ayın En Kritik Günleri
### Aylık Stratejik Tavsiye

Türkçe, kapsamlı ve ilham verici bir dil kullan.
Bu kişinin haritasının element yoğunluğunu aya özgü tavsiyelerle ilişkilendir.
"""

YEARLY_PROMPT = """
Sen deneyimli bir astrologsun. Aşağıdaki doğum haritası verilerini kullanarak
bu kişi için YILLIK öngörü analizini yap.

## DOĞUM HARİTASI VERİLERİ
{planets}

## AÇILAR (ASPECTS)
{aspects}

## ELEMENT DAĞILIMI
{elements}

## YIL BİLGİSİ
{period_info}

## YORUM FORMATI — Her başlık altında 4-6 cümle yaz:

### Yılın Ana Teması ve Büyük Resim
### Ocak–Mart: Yılın Açılışı
### Nisan–Haziran: Büyüme Sezonu
### Temmuz–Eylül: Dönüşüm Dönemi
### Ekim–Aralık: Hasat ve Kapanış
### Aşk, İlişkiler ve Aile
### Kariyer, Ambisyon ve Finansal Büyüme
### Kişisel Gelişim ve Bilinç Genişlemesi
### Sağlık ve Yaşam Tarzı
### Yılın En Kritik Astrolojik Dönemleri
### Genel Stratejik Tavsiye

Türkçe, vizyon açıcı ve dönüştürücü bir dil kullan.
Bu kişinin doğum haritasının yapısal güçlerini yılın akışıyla ilişkilendir.
Baskın elementi yıllık tavsiye çerçevesine entegre et.
"""

# Prompt seçici — analysis_type → prompt string
FORECAST_PROMPTS = {
    "daily":   DAILY_PROMPT,
    "weekly":  WEEKLY_PROMPT,
    "monthly": MONTHLY_PROMPT,
    "yearly":  YEARLY_PROMPT,
}

PERIOD_LABELS = {
    "daily":   "Günlük",
    "weekly":  "Haftalık",
    "monthly": "Aylık",
    "yearly":  "Yıllık",
}