# wropasi (wrong package silly)

> wropasi hâlâ geliştirme aşamasındadır ve şu an yalnızca Node.js ile hazırlanmış bir prototipi bulunmaktadır. Yazılımın kararlı sürümü Python ve GTK4 kullanılarak geliştirilecektir.

wropasi (veya Türkçesiyle "yalnış paket şapşik"), modern ve kullanıcı dostu Linux dağıtımlarında paket yönetimiyle ilgili bir UX sorununu çözen yardımcı bir yazılımdır.

## Bu yazılım ne işe yarıyor tam olarak?

Şöyle açıklayayım: Kullanıcı dostu standart bir Linux dağıtımında, paket yöneticinizle uyumlu olmayan bir paketi (örneğin Linux Mint üzerinde bir .rpm dosyası) yüklemeye çalıştığınızda; sistem ya masaüstü ortamınıza bağlı bir uygulama seçim penceresi açar ya da doğrudan arşiv yöneticinizi başlatır.

Bu durum, yeni bir Linux kullanıcısı için kafa karıştırıcı olabilir, çünkü Windows veya macOS'te genellikle tek bir paket yönetim sistemiyle işlem yapılır. Linux'ta ise çok sayıda paket yöneticisi ve paket formatı bulunması bu UX sorununu oluşturur. wropasi, işte bu sorunu çözmeyi amaçlar.

## wropasi bu sorunu nasıl çözüyor?

wropasi, soruna iki basit yöntemle yaklaşır: **Kullanıcıyı Bilgilendirmek** ve **Kullanıcıya Rehberlik Etme**.

**Kullanıcıyı Bilgilendirme** yöntemiyle, öncelikle yüklenmeye çalışılan paketin sistemle uyumlu olmadığı bilgisi kullanıcıya aktarılmalı. wropasi, bunu anlaşılır, hoş bir metin ve simgesel bir görsel ile yapar. Böylece kullanıcı, sisteminin mevcut paketi yükleyemeyeceğini öğrenmiş olur. Ancak herhangi bir rehberlik olmadan bu durum, kullanıcıyı yarı yolda bırakmak anlamına gelir.

**Kullanıcıya Rehberlik Etme** yöntemi ise tam da bu noktada devreye girer. Metin ve görsellerin ardından; kullanıcının sistemindeki yerel paket yönetimi ve yüklemeye çalıştığı paket formatına göre çeşitli seçenekler sunulur. Bu seçenekler arasında; paketi dağıtım depolarında, Flatpak veya Snap üzerinde aramak, "alien" aracıyla .deb veya .rpm formatına dönüştürmek ve diğer paket yönetim sistemleri için çeşitli yöntemler uygulamak yer alır. Bu yöntem sayesinde kullanıcı hem bilgilendirilmiş hem de ne yapacağını öğrenmiş olur. İşte bu kadar!

## Ekran Görüntüleri

Placeholder; henüz ekran görüntüsü veya GIF bulunmuyor.

## Geliştirme

wropasi'nin prototipi yalnızca Node.js kullanılarak geliştirilmiştir; prototip geliştirme süreci için henüz bir rehber bulunmamaktadır. Geliştirme rehberi, projenin Python tabanlı çalışan bir sürümü hazır olduğunda yayınlanacaktır.

## Lisans

wropasi, GPL-3.0 Lisansı ile lisanslanmıştır. Daha fazla bilgi için LICENSE dosyasına bakınız.