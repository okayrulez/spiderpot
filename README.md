# Spiderpot 🕷️

**Spiderpot**, ofis ortamlarında masanızdan kalktığınızda bilgisayarınızı kurcalamaya çalışan meraklı iş arkadaşlarınıza karşı geliştirebileceğiniz en komik ve etkili "tuzak" (honeypot) yazılımıdır! 

Bu yazılım tamamen arka planda görünmez olarak çalışır ve siz yoksayken bilgisayarınıza dokunanları anında tespit edip fotoğrafını çeker. Ayrıca ekranı anında kitleyen komik modlara sahiptir.

## 🚀 4 Harika İşlev (Mod)

Spiderpot'un arka planda çalışırken tetikleyebileceğiniz 4 farklı çalışma modu vardır:

### 1. Görünmez Tuzak Modu (Honeypot) 📸
* **Kısayol:** `Ctrl + 3` (veya belirlediğiniz kısayol)
* Bilgisayar ekranınızda hiçbir değişiklik olmaz! Ekranınız açık ve normal görünür. Ancak biri farenize dokunduğu, hareket ettirdiği veya tıkladığı anda kamera devreye girer ve **fotoğrafını çeker**.
* Çekilen fotoğraf tüm ekranlarda **3 saniye boyunca** kırmızı **YAKALANDIN!** uyarısıyla gösterilir, ardından ekran yeniden görünmez tuzak moduna döner.
* Suçüstü fotoğrafları ayrıca `Spiderpot_Yakalananlar` klasörüne kaydedilir.

### 2. Örümcek Modu 🕸️
* **Kısayol:** `Ctrl + 1` (veya belirlediğiniz kısayol)
* Biri bilgisayarınıza dokunduğu anda ekran anında donar, tüm Windows kısayolları (Ctrl+Alt+Del, Alt+Tab, Windows tuşu) devre dışı bırakılır ve fareniz kilitlenir.
* Ekranda devasa bir **Spider-Man Noir** resmi belirir ve bilgisayarınız kullanılamaz hale gelir!
* Temas algılandığında çekilen fotoğraf **YAKALANDIN!** yazısıyla 3 saniye gösterilir ve ardından Spider-Man ekranına geri dönülür.

### 3. Siyah Ekran Modu ⬛
* **Kısayol:** `Ctrl + 2` (veya belirlediğiniz kısayol)
* "Örümcek Modu" ile aynı koruma mekanizmalarına sahiptir ancak ekrana resim koymak yerine tüm ekranı **tamamen siyah** yapar.
* Bilgisayar kapalıymış veya bozulmuş gibi görünür. Fişini çekmeye çalışmalarını izleyebilirsiniz!
* Temas algılandığında çekilen fotoğraf **YAKALANDIN!** yazısıyla 3 saniye gösterilir ve ardından siyah ekrana geri dönülür.

### 4. Slayt Ekran Koruyucu Modu 🎞️
* **Kısayol:** `Ctrl + 4` (veya belirlediğiniz kısayol)
* `Assets/Slayt_Gorselleri` klasöründeki JPG, JPEG, PNG, BMP ve WebP görsellerini dosya adına göre sırayla oynatır.
* Her görsel ekranda **5 saniye** kalır; sonraki görsele yumuşak bir geçişle geçilir ve tüm monitörler tam ekran kaplanır.
* Temas algılandığında çekilen fotoğraf **YAKALANDIN!** yazısıyla 3 saniye gösterilir ve ardından slayt gösterisi yeniden başlar.

## 🛑 Kapatma / İptal
Uygulama aktifken bilgisayarı tekrar kullanabilmek için sadece sizin bildiğiniz bir **Gizli Çıkış Kısayolu** (Örn: `F12` veya `Ctrl+E`) bulunur. Bu tuşa basılana kadar sistem asla açılamaz!

## 🛠️ Nasıl Kurulur?
1. Slaytta kullanmak istediğiniz görselleri `Assets/Slayt_Gorselleri` klasörüne kopyalayın.
2. `Spiderpot_Kurulum.py` arayüzünü çalıştırarak kendi kısayol tuşlarınızı belirleyin ve istediğiniz Spider duvar kağıdını seçin.
3. **Kurulumu Başlat** düğmesine basarak görsellerle birlikte tek dosyalık `Spiderpot_Sistem.exe` uygulamasını derleyin.

---
*Not: Bu yazılım tamamen şaka ve ofis içi eğlence/güvenlik amacıyla geliştirilmiştir. Çok ciddiye almayınız!*
