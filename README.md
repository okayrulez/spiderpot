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
* Tuzak açıldığında tam ekran görünüm devreye girer; standart klavye ve fare girdileri çıkış tuşuna kadar bastırılır.
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
1. `dist/Spiderpot_Setup.exe` dosyasını kurulacak Windows bilgisayarına kopyalayın ve açın. Hedef bilgisayarda Python veya geliştirme aracı gerekmez.
2. **Görselleri Seç** düğmesiyle istediğiniz sayıda Ctrl+1 görseli belirleyin ve geçiş süresini girin.
3. Kısayolları ve otomatik başlangıç seçeneklerini ayarlayıp **Spiderpot'u Kur / Güncelle** düğmesine basın.
4. Uygulama `%LOCALAPPDATA%\Programs\Spiderpot` klasörüne kurulur. Masaüstü ve Başlat menüsü kısayolları oluşturulur; seçildiyse Windows başlangıcına eklenir.
5. Spiderpot, Windows **Yüklü uygulamalar** ekranından veya Setup içindeki **Kaldır** düğmesinden kaldırılabilir. Yakalanan fotoğraflar kaldırma sırasında korunur.

## 📦 Kurulum Sihirbazını EXE Yapma
`python Build_Setup_Exe.py` önce güncel `Spiderpot_Sistem.exe` dosyasını üretir, ardından onu kurulum paketinin içine gömerek `dist/Spiderpot_Setup.exe` oluşturur. Ortaya çıkan Setup tek başına başka bir Windows bilgisayarına gönderilebilir.

## 🏪 Microsoft Store / Ücretsiz İmzalama

Microsoft Store için EXE kurulum dosyası yerine MSIX paketi kullanılır. Store,
sertifikadan geçen MSIX paketini ücretsiz olarak imzalar.

1. Partner Center'da ürün adı ayrıldıktan sonra Product identity ekranındaki
   `Name`, `Publisher` ve `Publisher Display Name` değerlerini
   `Store/store_identity.json` dosyasına girin.
2. `python Build_MSIX.py` komutunu çalıştırın.
3. Gönderilecek paket `dist/Spiderpot_<sürüm>_x64_unsigned.msix` olarak üretilir.
   Dosyanın imzasız olması normaldir; Store gönderim sırasında yeniden imzalar.

Mağaza açıklamaları, gizlilik taslağı, sertifika test notları ve gönderim kontrol
listesi `Store` klasöründedir. `store_identity.json` içindeki `Placeholder`
değerleriyle normal derleme engellenir. Yalnızca yerel teknik ön paket gerektiğinde
`python Build_MSIX.py --allow-placeholder` kullanılabilir; bu paket mağazaya
yüklenmemelidir.

---
*Not: Bu yazılım tamamen şaka ve ofis içi eğlence/güvenlik amacıyla geliştirilmiştir. Çok ciddiye almayınız!*
