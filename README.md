# Spiderpot 🕷️

**Spiderpot**, ofis ortamlarında masanızdan kalktığınızda bilgisayarınızı kurcalamaya çalışan meraklı iş arkadaşlarınıza karşı geliştirebileceğiniz en komik ve etkili "tuzak" (honeypot) yazılımıdır! 

Bu yazılım tamamen arka planda görünmez olarak çalışır ve siz yoksayken bilgisayarınıza dokunanları anında tespit edip fotoğrafını çeker. Ayrıca ekranı anında kitleyen komik modlara sahiptir.

## 🚀 3 Harika İşlev (Mod)

Spiderpot'un arka planda çalışırken tetikleyebileceğiniz 3 farklı çalışma modu vardır:

### 1. Görünmez Tuzak Modu (Honeypot) 📸
* **Kısayol:** `Ctrl + 3` (veya belirlediğiniz kısayol)
* Bilgisayar ekranınızda hiçbir değişiklik olmaz! Ekranınız açık ve normal görünür. Ancak biri farenize dokunduğu, hareket ettirdiği veya tıkladığı anda kamera devreye girer ve **fotoğrafını çeker**.
* Çekilen fotoğraf tüm ekranlarda **3 saniye boyunca** kırmızı **YAKALANDIN!** uyarısıyla gösterilir, ardından ekran yeniden görünmez tuzak moduna döner.
* Suçüstü fotoğrafları ayrıca `Spiderpot_Yakalananlar` klasörüne kaydedilir.

### 2. Örümcek Modu 🕸️
* **Kısayol:** `Ctrl + 1` (veya belirlediğiniz kısayol)
* Biri bilgisayarınıza dokunduğu anda ekran anında donar, tüm Windows kısayolları (Ctrl+Alt+Del, Alt+Tab, Windows tuşu) devre dışı bırakılır ve fareniz kilitlenir.
* Kurulumda seçilen ana duvar kâğıdıyla `Assets/Slayt_Gorselleri` klasöründeki görseller tam ekran gösterilir.
* Tek görsel varsa sabit kalır; birden fazla görsel varsa kurulumda seçtiğiniz saniye aralığıyla akar ve aralarında yumuşak geçiş yapılır.
* Temas algılandığında çekilen fotoğraf **YAKALANDIN!** yazısıyla 3 saniye gösterilir ve ardından duvar kâğıdı akışına geri dönülür.

### 3. Siyah Ekran Modu ⬛
* **Kısayol:** `Ctrl + 2` (veya belirlediğiniz kısayol)
* "Örümcek Modu" ile aynı koruma mekanizmalarına sahiptir ancak ekrana resim koymak yerine tüm ekranı **tamamen siyah** yapar.
* Bilgisayar kapalıymış veya bozulmuş gibi görünür. Fişini çekmeye çalışmalarını izleyebilirsiniz!
* Temas algılandığında çekilen fotoğraf **YAKALANDIN!** yazısıyla 3 saniye gösterilir ve ardından siyah ekrana geri dönülür.

## 🛑 Kapatma / İptal
Uygulama aktifken bilgisayarı tekrar kullanabilmek için sadece sizin bildiğiniz bir **Gizli Çıkış Kısayolu** (Örn: `F12` veya `Ctrl+E`) bulunur. Bu tuşa basılana kadar sistem asla açılamaz!

## 🛠️ Nasıl Kurulur?
1. `Spiderpot_Kurulum.py` arayüzündeki **Çoklu Seç** düğmesine basın; `Ctrl+A`, `Ctrl` veya `Shift` kullanarak istediğiniz sayıda Ctrl+1 görseli seçin.
2. İlk seçilen görsel başlangıç duvar kâğıdı olur; diğerleri seçilen sırayla akışa eklenir. **Ctrl+1 Foto Geçiş Aralığı (sn)** alanından fotoğrafların kaç saniyede bir değişeceğini yazabilirsiniz. İsterseniz `Assets/Slayt_Gorselleri` klasörüne ayrıca görsel de kopyalayabilirsiniz.
3. **Bu PC'ye Kur** düğmesi mevcut yerel Spiderpot'u yeniler, başlangıç ayarını uygular ve yeni EXE'yi çalıştırır.
4. **Başka PC İçin EXE Üret** düğmesi ise mevcut kuruluma dokunmadan kayıt yerini seçtiğiniz tek dosyalık bir EXE üretir; dosyayı çalıştırmaz ve bu bilgisayara başlangıç kaydı eklemez.

---
*Not: Bu yazılım tamamen şaka ve ofis içi eğlence/güvenlik amacıyla geliştirilmiştir. Çok ciddiye almayınız!*
